from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.currencies import UAH, format_money
from app.db.models.recurring_payment import RecurringPayment
from app.db.models.user import User
from app.repositories.recurring_payment import RecurringPaymentRepository
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.schemas.notification import NotificationType
from app.services.analytics_service import MONTH_GENITIVE, ORDINALS, AnalyticsService
from app.services.recurring_detection import SUBSCRIPTION
from app.services.recurring_service import RecurringService

RECENT_DAYS = 7
FIRST_SCAN_GAP = timedelta(hours=1)
PACE_FIRST_DAY = 15
PACE_LAST_DAY = 20
USUAL_PACE_PCT = 5


@dataclass(frozen=True)
class NotificationDraft:
    type: NotificationType
    dedupe_key: str
    title: str
    body: str
    data: dict = field(default_factory=dict)


Check = Callable[[AsyncSession, User, datetime], Awaitable[list[NotificationDraft]]]


async def _subscriptions(db: AsyncSession, user: User, now: datetime) -> list[RecurringPayment]:
    rows = await RecurringService(db).list(user.id, SUBSCRIPTION, int(now.timestamp()))
    return [row for row in rows if row.cancelled_at is None]


async def new_subscriptions(db: AsyncSession, user: User, now: datetime) -> list[NotificationDraft]:
    rows = await _subscriptions(db, user, now)
    first_scan = await RecurringPaymentRepository(db).first_created_at(user.id)
    since = now - timedelta(days=RECENT_DAYS)
    return [
        NotificationDraft(
            type=NotificationType.NEW_SUBSCRIPTION,
            dedupe_key=f"new_subscription:{row.id}",
            title="Нова підписка",
            body=(
                f"{row.name}: {format_money(row.amount, row.currency_code)} щомісяця, списується вже "
                f"{ORDINALS.get(row.charges_count, f'{row.charges_count}-й')} місяць. Додали до твоїх підписок."
            ),
            data={"recurring_id": row.id},
        )
        for row in rows
        if row.created_at >= since and first_scan is not None and row.created_at > first_scan + FIRST_SCAN_GAP
    ]


async def subscription_price_increases(db: AsyncSession, user: User, now: datetime) -> list[NotificationDraft]:
    since = int((now - timedelta(days=RECENT_DAYS)).timestamp())
    return [
        NotificationDraft(
            type=NotificationType.SUBSCRIPTION_PRICE,
            dedupe_key=f"subscription_price:{row.id}:{row.price_changed_at}",
            title="Підписка подорожчала",
            body=(
                f"{row.name}: було {format_money(row.previous_amount, row.currency_code)}, "
                f"тепер {format_money(row.amount, row.currency_code)} "
                f"(+{round((row.amount - row.previous_amount) / row.previous_amount * 100)}%)."
            ),
            data={"recurring_id": row.id},
        )
        for row in await _subscriptions(db, user, now)
        if row.previous_amount and row.price_changed_at and row.price_changed_at >= since
        and row.amount > row.previous_amount
    ]


async def month_pace(db: AsyncSession, user: User, now: datetime) -> list[NotificationDraft]:
    if not PACE_FIRST_DAY <= now.day <= PACE_LAST_DAY:
        return []
    pace = await AnalyticsService(db, user.id, DEFAULT_TIMEZONE, today=now.date()).month_pace()
    if pace is None or pace.usual <= 0 or pace.spent <= 0:
        return []
    change = round((pace.spent - pace.usual) / pace.usual * 100)
    period = f"З 1 по {pace.day} {MONTH_GENITIVE[now.month - 1]}"
    spent = format_money(round(pace.spent, -2), UAH)
    if change <= -USUAL_PACE_PCT:
        body = f"Ти молодець: {period.lower()} витрачено {spent}, це на {-change}% менше, ніж зазвичай."
    elif change < USUAL_PACE_PCT:
        body = f"{period} витрачено {spent}. Йдеш у звичному темпі."
    else:
        body = f"{period} витрачено {spent}, це на {change}% більше, ніж зазвичай."
        if pace.top_category is not None:
            body += f" Найбільше зросла категорія «{pace.top_category.name}»: +{format_money(round(pace.top_category_diff, -2), UAH)}."
    return [NotificationDraft(
        type=NotificationType.MONTH_PACE,
        dedupe_key=f"month_pace:{pace.month}",
        title="Темп місяця",
        body=body,
        data={"month": pace.month},
    )]


CHECKS: dict[NotificationType, Check] = {
    NotificationType.SUBSCRIPTION_PRICE: subscription_price_increases,
    NotificationType.NEW_SUBSCRIPTION: new_subscriptions,
    NotificationType.MONTH_PACE: month_pace,
}
