import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.mcc_codes import MccCode
from app.repositories.account import AccountRepository
from app.repositories.category import CategoryRepository
from app.repositories.jar import JarRepository
from app.repositories.merchant_mapping import MerchantCategoryMappingRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.categorization import CategorizationCandidate
from app.services.ai.base import CategorizationAIClient
from app.services.merchant_key import build_merchant_key

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7

# An outgoing payment can never be income; anything else may be an expense,
# a refund (incoming, expense kind), a transfer or unknown.
OUTGOING_KINDS = ("expense", "transfer", "unknown")


class CategorizationAIError(Exception):
    """Raised when the AI client itself fails (network/API error), as opposed
    to succeeding with a low-confidence result."""


class NotManualTransactionError(Exception):
    """Raised when editing/deleting is attempted on a Monobank-synced
    transaction, which must stay a faithful copy of the bank's record."""


class CategoryDirectionError(ValueError):
    """Raised when a user picks an income category for money going out."""


def check_category_fits_amount(kind: str, amount: int) -> None:
    """Outgoing money is never income. The opposite is allowed: a positive
    amount in an expense category is a refund."""
    if kind == "income" and amount < 0:
        raise CategoryDirectionError("An income category needs a positive amount")


def _mapping_fits_direction(kind: str, amount: int) -> bool:
    """A mapping is keyed by merchant, not by direction. One learned from a
    purchase (expense) must not label money coming back from that merchant -
    that could be a refund or, for a person, a transfer to the user - and one
    learned from income must not label an outgoing payment."""
    if kind == "expense":
        return amount < 0
    if kind == "income":
        return amount > 0
    return True


class CategorizationService:

    def __init__(self, db: AsyncSession, ai_client: CategorizationAIClient | None = None):
        self.db = db
        self.ai_client = ai_client
        self.transactions = TransactionRepository(db)
        self.categories = CategoryRepository(db)
        self.mappings = MerchantCategoryMappingRepository(db)
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)

    async def categorize(self, transaction_id: int) -> None:
        # Row lock: the webhook path, backfill and the sweeper can all reach
        # the same transaction; whoever gets here second skips it.
        transaction = await self.transactions.get_for_categorization(transaction_id)

        if transaction is None:
            logger.info("Categorization skipped: transaction id=%s missing or being categorized", transaction_id)
            return

        if transaction.category_id is not None:
            await self.db.rollback()
            logger.info("Categorization skipped: transaction id=%s already categorized", transaction_id)
            return

        # Linked first: the pair is a strong hint that this is the user's own
        # money moving, and it's useful data on its own.
        await self._try_link_transfer_pair(transaction)

        merchant_key = build_merchant_key(transaction.description)

        if transaction.mcc is not None:
            mapping = await self.mappings.get(transaction.user_id, merchant_key, transaction.mcc)
            mapped_category = await self.categories.get_by_id(mapping.category_id) if mapping else None
            if mapped_category is not None and _mapping_fits_direction(mapped_category.kind, transaction.amount):
                # A mapping learned from a low-confidence AI guess still gets
                # used (so the same merchant doesn't keep re-triggering AI
                # calls), but the transaction inherits that same low-confidence
                # flag instead of silently looking "resolved".
                mapping_unsure = mapping.confidence is not None and mapping.confidence < CONFIDENCE_THRESHOLD
                self.transactions.set_category(
                    transaction,
                    category_id=mapping.category_id,
                    source="mapping_low_confidence" if mapping_unsure else "mapping",
                    confidence=mapping.confidence,
                    merchant_mapping_id=mapping.id,
                )
                await self.db.commit()
                logger.info(
                    "Transaction categorized from mapping id=%s category_id=%s",
                    transaction.id, mapping.category_id,
                )
                return

        selectable = await self.categories.get_selectable_categories(
            kinds=OUTGOING_KINDS if transaction.amount < 0 else None,
        )
        by_slug = {c.slug: c for c in selectable}
        names = {c.id: c.name for c in selectable}
        candidates = [
            CategorizationCandidate(slug=c.slug, name=c.name, kind=c.kind, parent_name=names.get(c.parent_id))
            for c in selectable
        ]

        try:
            result = await self.ai_client.classify(
                description=transaction.description,
                mcc=transaction.mcc,
                mcc_name=await self._get_mcc_name(transaction.mcc),
                amount=transaction.amount,
                counter_name=transaction.counter_name,
                hints=await self._build_hints(transaction),
                candidates=candidates,
            )
        except Exception as e:
            raise CategorizationAIError(f"AI classify() failed for transaction id={transaction_id}") from e

        category: Category | None = by_slug.get(result.category_slug) if result.category_slug else None
        confidence = result.confidence
        if category is None:
            logger.warning(
                "AI gave no usable category (slug=%s) for transaction id=%s, falling back to unknown",
                result.category_slug, transaction.id,
            )
            category = await self.categories.get_unknown_category()
            confidence = 0.0

        is_confident = confidence >= CONFIDENCE_THRESHOLD
        source = "ai" if is_confident else "ai_low_confidence"

        self.transactions.set_category(
            transaction,
            category_id=category.id,
            source=source,
            confidence=confidence,
        )

        if transaction.mcc is not None and _mapping_fits_direction(category.kind, transaction.amount):
            await self.mappings.upsert(
                user_id=transaction.user_id,
                merchant_key=merchant_key,
                mcc=transaction.mcc,
                category_id=category.id,
                source=source,
                confidence=confidence,
            )

        await self.db.commit()
        logger.info(
            "Transaction categorized via AI id=%s category=%s confidence=%.2f source=%s",
            transaction.id, category.slug, confidence, source,
        )

    async def _build_hints(self, transaction) -> list[str]:
        """Facts from our own data the AI can't see in the transaction
        itself - mostly whether the money stays within the user's own
        accounts, which decides transfer vs income/expense."""
        hints: list[str] = []

        if transaction.jar_id is not None:
            jar = await self.jars.get_by_id_for_user(transaction.jar_id, transaction.user_id)
            title = f" «{jar.title}»" if jar else ""
            hints.append(f"This transaction is on the user's own jar (savings){title}.")
        elif transaction.account_id is not None:
            account = await self.accounts.get_by_id_for_user(transaction.account_id, transaction.user_id)
            if account is not None and account.account_type == "fop":
                hints.append("This is the user's FOP (sole proprietor) business account.")

        if transaction.transfer_pair_id is not None:
            hints.append(
                "An opposite transaction for the same amount happened at the same time "
                "on another of the user's own accounts or jars."
            )

        if transaction.counter_iban:
            own_ibans = {a.iban for a in await self.accounts.list_for_user(transaction.user_id) if a.iban}
            if transaction.counter_iban in own_ibans:
                hints.append("The counterparty IBAN is one of the user's own accounts.")

        return hints

    async def _get_mcc_name(self, mcc: int | None) -> str | None:
        if mcc is None:
            return None
        result = await self.db.execute(select(MccCode.name).where(MccCode.code == mcc))
        return result.scalar_one_or_none()

    async def _try_link_transfer_pair(self, transaction) -> None:
        if transaction.transfer_pair_id is not None:
            return

        candidate = await self.transactions.find_unpaired_transfer_candidate(
            user_id=transaction.user_id,
            amount=-transaction.amount,
            time=transaction.time,
            exclude_id=transaction.id,
            account_id=transaction.account_id,
            jar_id=transaction.jar_id,
        )
        if candidate is None:
            return

        transaction.transfer_pair_id = candidate.id
        candidate.transfer_pair_id = transaction.id
        logger.info(
            "Linked transfer pair: id=%s <-> id=%s",
            transaction.id, candidate.id,
        )

    async def mark_categorization_failed(self, transaction_id: int) -> None:
        # Session may be mid-way through a failed categorize(); start clean.
        await self.db.rollback()
        transaction = await self.transactions.get_by_id(transaction_id)
        if transaction is None or transaction.category_id is not None:
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
        check_category_fits_amount(category.kind, transaction.amount)

        self.transactions.set_category(transaction, category_id=category.id, source="user")

        # A refund re-labelled by hand says nothing about the merchant's
        # purchases, so it doesn't overwrite the merchant's mapping.
        if transaction.mcc is not None and _mapping_fits_direction(category.kind, transaction.amount):
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

    async def edit_manual_transaction(
        self,
        transaction_id: int,
        user_id: int,
        description: str | None = None,
        amount: int | None = None,
        category_id: int | None = None,
        comment: str | None = None,
        time: int | None = None,
    ):
        transaction = await self.transactions.get_by_id_for_user(transaction_id, user_id)
        if transaction is None:
            return None

        if transaction.source != "manual":
            raise NotManualTransactionError("Only manually created transactions can be edited")

        category = None
        if category_id is not None:
            category = await self.categories.get_selectable_by_id(category_id)
            if category is None:
                raise ValueError("Category not found or not selectable")

        # Either side may change, so check the pair the transaction ends up with.
        final_category = category or await self.categories.get_by_id(transaction.category_id)
        if final_category is not None:
            check_category_fits_amount(final_category.kind, amount if amount is not None else transaction.amount)

        self.transactions.update_manual_fields(
            transaction, description=description, amount=amount, comment=comment, time=time,
        )
        if category is not None:
            self.transactions.set_category(transaction, category_id=category.id, source="user")

        await self.db.commit()
        logger.info("Manual transaction edited id=%s", transaction.id)

        return transaction

    async def delete_manual_transaction(self, transaction_id: int, user_id: int) -> bool:
        transaction = await self.transactions.get_by_id_for_user(transaction_id, user_id)
        if transaction is None:
            return False

        if transaction.source != "manual":
            raise NotManualTransactionError("Only manually created transactions can be deleted")

        await self.transactions.delete(transaction)
        await self.db.commit()
        logger.info("Manual transaction deleted id=%s", transaction_id)

        return True
