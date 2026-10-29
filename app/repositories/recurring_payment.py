from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models.categories import Category
from app.db.models.recurring_payment import RecurringPayment
from app.db.models.transaction import TransactionRaw
from app.db.models.user import User
from app.services.merchant_key import build_merchant_key
from app.services.recurring_detection import Charge


class RecurringPaymentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def lock_user(self, user_id: int) -> None:
        await self.db.execute(select(User.id).where(User.id == user_id).with_for_update())

    async def charges(self, user_id: int, since: int) -> list[Charge]:
        parent = aliased(Category)
        result = await self.db.execute(
            select(
                TransactionRaw.id,
                TransactionRaw.time,
                TransactionRaw.description,
                TransactionRaw.mcc,
                TransactionRaw.category_id,
                Category.slug,
                parent.slug,
                TransactionRaw.currency_code,
                TransactionRaw.amount,
                TransactionRaw.operation_amount,
                TransactionRaw.amount_uah,
                TransactionRaw.recurring_payment_id,
            )
            .join(Category, Category.id == TransactionRaw.category_id)
            .outerjoin(parent, parent.id == Category.parent_id)
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.amount < 0,
                TransactionRaw.amount_uah.is_not(None),
                TransactionRaw.time >= since,
                Category.kind == "expense",
            )
        )
        return [
            Charge(
                transaction_id=transaction_id,
                time=moment,
                merchant_key=build_merchant_key(description) or description.strip().lower(),
                description=description,
                mcc=mcc,
                category_id=category_id,
                category_slug=slug,
                parent_slug=parent_slug,
                currency_code=currency_code,
                amount=abs(operation_amount if operation_amount is not None else amount),
                amount_uah=-amount_uah,
                recurring_payment_id=recurring_payment_id,
            )
            for (
                transaction_id, moment, description, mcc, category_id, slug, parent_slug,
                currency_code, amount, operation_amount, amount_uah, recurring_payment_id,
            ) in result.all()
        ]

    async def list_for_user(self, user_id: int) -> list[RecurringPayment]:
        result = await self.db.execute(
            select(RecurringPayment)
            .where(RecurringPayment.user_id == user_id)
            .order_by(RecurringPayment.id)
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def first_created_at(self, user_id: int) -> datetime | None:
        result = await self.db.execute(
            select(func.min(RecurringPayment.created_at)).where(RecurringPayment.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, payment_id: int, user_id: int) -> RecurringPayment | None:
        result = await self.db.execute(
            select(RecurringPayment).where(RecurringPayment.id == payment_id, RecurringPayment.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def link(self, transaction_ids: list[int], payment_id: int | None) -> None:
        await self.db.execute(
            update(TransactionRaw).where(TransactionRaw.id.in_(transaction_ids)).values(recurring_payment_id=payment_id)
        )

    async def unlink_except(self, user_id: int, keep_ids: list[int]) -> None:
        await self.db.execute(
            update(TransactionRaw)
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.recurring_payment_id.is_not(None),
                TransactionRaw.id.not_in(keep_ids),
            )
            .values(recurring_payment_id=None)
        )

    async def transactions(self, payment_id: int) -> list[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw)
            .where(TransactionRaw.recurring_payment_id == payment_id)
            .order_by(TransactionRaw.time.desc(), TransactionRaw.id.desc())
        )
        return list(result.scalars().all())
