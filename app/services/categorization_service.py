import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcc_codes import MccCode
from app.repositories.category import CategoryRepository
from app.repositories.merchant_mapping import MerchantCategoryMappingRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.transaction_category import TransactionCategoryRepository
from app.schemas.categorization import CategorizationCandidate
from app.services.ai.base import CategorizationAIClient
from app.services.merchant_key import build_merchant_key

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7


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
        self.transaction_categories = TransactionCategoryRepository(db)

    async def categorize(self, transaction_id: int) -> None:
        transaction = await self.transactions.get_by_id(transaction_id)

        if transaction is None:
            logger.warning("Categorization skipped: transaction not found id=%s", transaction_id)
            return

        if transaction.mcc is None:
            logger.info("Categorization skipped: no MCC on transaction id=%s", transaction_id)
            return

        merchant_key = build_merchant_key(transaction.description)

        mapping = await self.mappings.get(transaction.user_id, merchant_key, transaction.mcc)
        if mapping is not None:
            await self.transaction_categories.create(
                transaction_id=transaction.id,
                category_id=mapping.category_id,
                source="mapping",
                merchant_mapping_id=mapping.id,
            )
            await self.db.commit()
            logger.info(
                "Transaction categorized from mapping id=%s category_id=%s",
                transaction.id, mapping.category_id,
            )
            return

        candidates = [
            CategorizationCandidate(slug=c.slug, name=c.name)
            for c in await self.categories.get_leaf_categories()
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

        await self.transaction_categories.create(
            transaction_id=transaction.id,
            category_id=category.id,
            source=source,
            confidence=result.confidence,
        )

        if is_confident:
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

    async def _get_mcc_name(self, mcc: int) -> str | None:
        result = await self.db.execute(select(MccCode.name).where(MccCode.code == mcc))
        return result.scalar_one_or_none()

    async def mark_categorization_failed(self, transaction_id: int) -> None:
        """Last resort after retries are exhausted: flag the transaction for
        manual review instead of leaving it silently uncategorized."""
        category = await self.categories.get_unknown_category()
        await self.transaction_categories.upsert(
            transaction_id=transaction_id,
            category_id=category.id,
            source="ai_failed",
        )
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

        await self.transaction_categories.upsert(
            transaction_id=transaction.id,
            category_id=category.id,
            source="user",
        )

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
