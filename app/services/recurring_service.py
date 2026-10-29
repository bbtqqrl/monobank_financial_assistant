import time
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recurring_payment import RecurringPayment
from app.repositories.recurring_payment import RecurringPaymentRepository
from app.services.errors import InvalidRequestError, NotFoundError
from app.services.recurring_detection import (
    DAY_SECONDS,
    SUBSCRIPTION,
    Cluster,
    cluster_charges,
    detect_kind,
    is_whole_merchant,
    payment_state,
    similar,
    typical_amounts,
)

LOOKBACK_DAYS = 400


def _matches(row: RecurringPayment, cluster: Cluster) -> bool:
    if row.merchant_key != cluster.merchant_key or row.currency_code != cluster.currency_code:
        return False
    return is_whole_merchant(cluster) or any(similar(row.amount, charge.amount) for charge in cluster.charges)


def state(row: RecurringPayment, now: int) -> str:
    confirmed = row.user_kind is not None and row.cancelled_at is None
    return payment_state(row.last_charge_at, row.period_days, row.kind, now, confirmed)


def _untouched(row: RecurringPayment) -> bool:
    return row.user_kind is None and row.declined_kind is None and row.cancelled_at is None


def _apply(row: RecurringPayment, cluster: Cluster, kind: str | None) -> None:
    row.kind = kind
    row.amount, row.amount_uah = typical_amounts(cluster, kind)
    row.period_days = cluster.period_days
    row.first_charge_at = cluster.charges[0].time
    row.last_charge_at = cluster.last.time
    row.charges_count = len(cluster.charges)
    row.mcc = cluster.mcc
    row.category_id = cluster.category_id
    if row.cancelled_at is not None and cluster.last.time > row.cancelled_at:
        row.cancelled_at = None


class RecurringService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringPaymentRepository(db)

    async def refresh(self, user_id: int, now: int | None = None) -> list[RecurringPayment]:
        now = now or int(time.time())
        await self.repo.lock_user(user_id)
        charges = await self.repo.charges(user_id, now - LOOKBACK_DAYS * DAY_SECONDS)
        free = await self.repo.list_for_user(user_id)
        clusters = sorted(cluster_charges(charges), key=lambda cluster: -cluster.last.time)

        created: list[RecurringPayment] = []
        linked: list[tuple[RecurringPayment, Cluster]] = []
        for cluster in clusters:
            row = next((row for row in free if _matches(row, cluster)), None)
            kind = row.user_kind if row is not None and row.user_kind else detect_kind(
                cluster, row.declined_kind if row is not None else None,
            )
            if row is None:
                if kind is None or payment_state(cluster.last.time, cluster.period_days, kind, now) == "inactive":
                    continue
                row = RecurringPayment(
                    user_id=user_id, merchant_key=cluster.merchant_key, name=cluster.name,
                    currency_code=cluster.currency_code,
                )
                self.db.add(row)
                created.append(row)
            else:
                free.remove(row)
            _apply(row, cluster, kind)
            if kind is not None:
                linked.append((row, cluster))

        for row in free:
            if _untouched(row):
                await self.db.delete(row)
            else:
                row.kind = row.user_kind
        await self.db.flush()

        wanted = {charge.transaction_id: row.id for row, cluster in linked for charge in cluster.charges}
        current = {charge.transaction_id: charge.recurring_payment_id for charge in charges}
        await self.repo.unlink_except(user_id, list(wanted))
        changes: dict[int, list[int]] = defaultdict(list)
        for transaction_id, payment_id in wanted.items():
            if current.get(transaction_id) != payment_id:
                changes[payment_id].append(transaction_id)
        for payment_id, transaction_ids in changes.items():
            await self.repo.link(transaction_ids, payment_id)
        await self.db.commit()
        return created

    async def list(self, user_id: int, kind: str | None = None) -> list[RecurringPayment]:
        now = int(time.time())
        await self.refresh(user_id, now)
        rows = await self.repo.list_for_user(user_id)
        return [
            row for row in rows
            if row.kind is not None and (kind is None or row.kind == kind)
            and not (row.kind == SUBSCRIPTION and state(row, now) == "inactive")
        ]

    async def get(self, payment_id: int, user_id: int) -> RecurringPayment:
        row = await self.repo.get_for_user(payment_id, user_id)
        if row is None or row.kind is None:
            raise NotFoundError("Recurring payment not found")
        return row

    async def transactions(self, payment_id: int):
        return await self.repo.transactions(payment_id)

    async def update(
        self,
        payment_id: int,
        user_id: int,
        answer: str | None = None,
        kind: str | None = None,
        name: str | None = None,
    ) -> RecurringPayment:
        if answer == "decline" and kind is not None:
            raise InvalidRequestError("Can't decline and set kind at once")
        row = await self.get(payment_id, user_id)
        if name is not None:
            row.name = name
        if kind is not None:
            row.kind = row.user_kind = kind
            row.declined_kind = None
        if answer == "confirm":
            row.user_kind = row.kind
            row.declined_kind = None
        elif answer == "decline":
            row.declined_kind = row.kind
            row.user_kind = None
        elif answer == "cancel":
            row.cancelled_at = int(time.time())
        elif answer == "resume":
            row.cancelled_at = None
        await self.db.commit()
        if answer == "decline":
            await self.refresh(user_id)
        await self.db.refresh(row)
        return row
