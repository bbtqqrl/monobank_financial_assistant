import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcc_codes import MccCode
from app.repositories.budget import BudgetRepository
from app.repositories.category import CategoryRepository
from app.repositories.merchant_mapping import MerchantCategoryMappingRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.categorization import CategorizationCandidate
from app.services.ai.base import CategorizationAIClient
from app.services.merchant_key import build_merchant_key
from app.services.transfer_mcc import TRANSFER_MCC_CODES

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7

JAR_MOVEMENT_CATEGORY_SLUG = "zaoshchadzhennia"
TRANSFER_MCC_CATEGORY_SLUG = "perekazy"


class CategorizationAIError(Exception):
    """Raised when the AI client itself fails (network/API error), as opposed
    to succeeding with a low-confidence result."""


class CategorizationService:

    def __init__(self, db: AsyncSession, ai_client: CategorizationAIClient | None = None):
        self.db = db
        self.ai_client = ai_client
        self.transactions = TransactionRepository(db)
        self.categories = CategoryRepository(db)
        self.mappings = MerchantCategoryMappingRepository(db)
        self.budgets = BudgetRepository(db)

    async def categorize(self, transaction_id: int) -> None:
        transaction = await self.transactions.get_by_id(transaction_id)

        if transaction is None:
            logger.warning("Categorization skipped: transaction not found id=%s", transaction_id)
            return

        if transaction.mcc is not None:
            merchant_key = build_merchant_key(transaction.description)
            mapping = await self.mappings.get(transaction.user_id, merchant_key, transaction.mcc)
            if mapping is not None:
                self.transactions.set_category(
                    transaction,
                    category_id=mapping.category_id,
                    source="mapping",
                    merchant_mapping_id=mapping.id,
                )
                await self._adjust_budget(transaction.user_id, mapping.category_id, transaction.amount, sign=1)
                await self.db.commit()
                logger.info(
                    "Transaction categorized from mapping id=%s category_id=%s",
                    transaction.id, mapping.category_id,
                )
                return

        rule_slug = self._determine_rule_category_slug(transaction)
        if rule_slug is not None:
            await self._try_link_transfer_pair(transaction)
            await self._apply_rule_category(transaction, rule_slug)
            return

        candidates = [
            CategorizationCandidate(slug=c.slug, name=c.name)
            for c in await self.categories.get_selectable_categories()
        ]

        try:
            result = await self.ai_client.classify(
                description=transaction.description,
                mcc=transaction.mcc,
                mcc_name=await self._get_mcc_name(transaction.mcc),
                amount=transaction.amount,
                counter_name=transaction.counter_name,
                candidates=candidates,
            )
        except Exception as e:
            raise CategorizationAIError(f"AI classify() failed for transaction id={transaction_id}") from e

        category = await self.categories.get_by_slug(result.category_slug)
        if category is None:
            logger.warning(
                "AI returned unknown category slug=%s, falling back to 'nevidome'",
                result.category_slug,
            )
            category = await self.categories.get_unknown_category()

        is_confident = result.confidence >= CONFIDENCE_THRESHOLD
        source = "ai" if is_confident else "ai_low_confidence"

        self.transactions.set_category(
            transaction,
            category_id=category.id,
            source=source,
            confidence=result.confidence,
        )
        await self._adjust_budget(transaction.user_id, category.id, transaction.amount, sign=1)

        if is_confident and transaction.mcc is not None:
            await self.mappings.upsert(
                user_id=transaction.user_id,
                merchant_key=merchant_key,
                mcc=transaction.mcc,
                category_id=category.id,
                source="ai",
            )

        await self.db.commit()
        logger.info(
            "Transaction categorized via AI id=%s category=%s confidence=%.2f source=%s",
            transaction.id, category.slug, result.confidence, source,
        )

    async def _adjust_budget(self, user_id: int, category_id: int | None, amount: int, sign: int) -> None:
        """Only expenses (negative amount) count against a budget. `sign` is
        +1 to add spend to a budget, -1 to reverse a previous contribution
        (e.g. when a transaction is re-categorized)."""
        if category_id is None or amount >= 0:
            return

        budget = await self.budgets.get_by_category_for_user(user_id, category_id)
        if budget is None:
            return

        self.budgets.adjust_current_amount(budget, sign * -amount)

    async def _get_mcc_name(self, mcc: int | None) -> str | None:
        if mcc is None:
            return None
        result = await self.db.execute(select(MccCode.name).where(MccCode.code == mcc))
        return result.scalar_one_or_none()

    async def _try_link_transfer_pair(self, transaction) -> None:
        candidate = await self.transactions.find_unpaired_transfer_candidate(
            user_id=transaction.user_id,
            amount=-transaction.amount,
            time=transaction.time,
            exclude_id=transaction.id,
        )
        if candidate is None:
            return

        transaction.transfer_pair_id = candidate.id
        candidate.transfer_pair_id = transaction.id
        logger.info(
            "Linked transfer pair: id=%s <-> id=%s",
            transaction.id, candidate.id,
        )

    @staticmethod
    def _determine_rule_category_slug(transaction) -> str | None:
        if transaction.jar_id is not None:
            return JAR_MOVEMENT_CATEGORY_SLUG
        if transaction.mcc is None or transaction.mcc in TRANSFER_MCC_CODES:
            return TRANSFER_MCC_CATEGORY_SLUG
        return None

    async def _apply_rule_category(self, transaction, category_slug: str) -> None:
        category = await self.categories.get_by_slug(category_slug)
        if category is None:
            logger.error(
                "Rule category slug=%s is missing from the database, skipping transaction id=%s",
                category_slug, transaction.id,
            )
            return

        self.transactions.set_category(transaction, category_id=category.id, source="rule")
        await self._adjust_budget(transaction.user_id, category.id, transaction.amount, sign=1)
        await self.db.commit()
        logger.info(
            "Transaction categorized by rule id=%s category=%s",
            transaction.id, category.slug,
        )

    async def mark_categorization_failed(self, transaction_id: int) -> None:
        transaction = await self.transactions.get_by_id(transaction_id)
        if transaction is None:
            return

        category = await self.categories.get_unknown_category()
        self.transactions.set_category(transaction, category_id=category.id, source="ai_failed")
        await self.db.commit()
        logger.error(
            "Transaction id=%s categorization permanently failed after retries; flagged for manual review",
            transaction_id,
        )

    async def apply_user_category(self, transaction_id: int, user_id: int, category_id: int):
        transaction = await self.transactions.get_by_id_for_user(transaction_id, user_id)
        if transaction is None:
            return None

        category = await self.categories.get_selectable_by_id(category_id)
        if category is None:
            raise ValueError("Category not found or not selectable")

        old_category_id = transaction.category_id
        await self._adjust_budget(transaction.user_id, old_category_id, transaction.amount, sign=-1)

        self.transactions.set_category(transaction, category_id=category.id, source="user")
        await self._adjust_budget(transaction.user_id, category.id, transaction.amount, sign=1)

        if transaction.mcc is not None:
            merchant_key = build_merchant_key(transaction.description)
            await self.mappings.upsert(
                user_id=transaction.user_id,
                merchant_key=merchant_key,
                mcc=transaction.mcc,
                category_id=category.id,
                source="user",
            )

        await self.db.commit()
        logger.info(
            "Transaction category set by user id=%s category=%s",
            transaction.id, category.slug,
        )

        return transaction
