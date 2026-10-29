import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.currencies import UAH, format_money
from app.db.models.recurring_payment import RecurringPayment
from app.db.models.user import User
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.repositories.notification import NotificationRepository
from app.repositories.recurring_payment import RecurringPaymentRepository
from app.schemas.analytics import WeekSummary
from app.schemas.notification import NotificationType
from app.services.analytics_service import MONTH_GENITIVE, ORDINALS, AnalyticsService
from app.services.llm.client import Completed, LLMClient
from app.services.recurring_detection import SUBSCRIPTION
from app.services.recurring_service import RecurringService

logger = logging.getLogger(__name__)

RECENT_DAYS = 7
FIRST_SCAN_GAP = timedelta(hours=1)
PACE_FIRST_DAY = 15
PACE_LAST_DAY = 20
USUAL_PACE_PCT = 5
SUNDAY = 6
SUMMARY_MAX_TOKENS = 1024
SUMMARY_MAX_LENGTH = 300
RARE_WEEKLY_AMOUNT = 10_000

WEEKLY_SUMMARY_PROMPT = """Ти пишеш недільне push-сповіщення з підсумком тижня витрат для застосунку особистих фінансів.
Отримаєш готові факти. Напиши 2-3 коротких речення українською, звертаючись на «ти», загалом до 250 символів.
- Почни з головного: скільки витрачено і як це порівняно зі звичайним тижнем, якщо порівняння є.
- Далі одне найцікавіше спостереження з фактів: категорія, що помітно вища чи нижча за звичайну, або велика покупка.
- Використовуй лише надані факти й готові числа, нічого не рахуй і не вигадуй. Суми пиши так само, як у фактах.
- Без привітань, без емодзі, без лапок навколо всього тексту, без порад загального характеру.
- Не вживай дієслів минулого часу з родом («витратив», «витратила»): пиши «витрачено», «пішло».
Відповідай лише текстом сповіщення."""


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
    spent = _uah(pace.spent)
    if change <= -USUAL_PACE_PCT:
        body = f"Ти молодець: {period.lower()} витрачено {spent}, це на {-change}% менше, ніж зазвичай."
    elif change < USUAL_PACE_PCT:
        body = f"{period} витрачено {spent}. Йдеш у звичному темпі."
    else:
        body = f"{period} витрачено {spent}, це на {change}% більше, ніж зазвичай."
        if pace.top_category is not None:
            body += f" Найбільше зросла категорія «{pace.top_category.name}»: +{_uah(pace.top_category_diff)}."
    return [NotificationDraft(
        type=NotificationType.MONTH_PACE,
        dedupe_key=f"month_pace:{pace.month}",
        title="Темп місяця",
        body=body,
        data={"month": pace.month},
    )]


def _day(day: date) -> str:
    return f"{day.day} {MONTH_GENITIVE[day.month - 1]}"


def _uah(amount: int) -> str:
    return format_money(round(amount, -2), UAH)


def _change(amount: int, usual: int | None) -> int | None:
    return round((amount - usual) / usual * 100) if usual else None


def week_facts(summary: WeekSummary) -> str:
    lines = [
        f"Тиждень: {_day(summary.week_start)} – {_day(summary.week_end)}",
        f"Витрачено: {_uah(summary.spent)}, покупок: {summary.count}",
    ]
    change = _change(summary.spent, summary.usual)
    if change is None:
        lines.append("Звичайний тиждень: історії для порівняння ще мало")
    else:
        lines.append(f"Звичайний тиждень: {_uah(summary.usual)}, різниця {change:+d}%")
    for category in summary.categories:
        if category.usual is None:
            usual = ""
        elif category.usual < RARE_WEEKLY_AMOUNT:
            usual = ", зазвичай на це майже не витрачається"
        else:
            usual = f", зазвичай {_uah(category.usual)} на тиждень"
        lines.append(f"Категорія «{category.name}»: {_uah(category.spent)}{usual}")
    if summary.biggest is not None:
        lines.append(
            f"Найбільша покупка: {summary.biggest.description} — {_uah(summary.biggest.amount)} "
            f"(«{summary.biggest.category}»)"
        )
    return "\n".join(lines)


def week_fallback(summary: WeekSummary) -> str:
    text = f"За тиждень витрачено {_uah(summary.spent)}"
    change = _change(summary.spent, summary.usual)
    if change is not None and change <= -USUAL_PACE_PCT:
        text += f", на {-change}% менше, ніж зазвичай"
    elif change is not None and change >= USUAL_PACE_PCT:
        text += f", на {change}% більше, ніж зазвичай"
    text += "."
    if summary.categories:
        top = summary.categories[0]
        text += f" Найбільше пішло на «{top.name}»: {_uah(top.spent)}."
    return text


async def write_week_summary(summary: WeekSummary, user_id: int, llm: LLMClient | None = None) -> str:
    try:
        message = None
        async for event in (llm or LLMClient()).stream(
            purpose="weekly_summary",
            system=WEEKLY_SUMMARY_PROMPT,
            messages=[{"role": "user", "content": week_facts(summary)}],
            user_id=user_id,
            max_tokens=SUMMARY_MAX_TOKENS,
        ):
            if isinstance(event, Completed):
                message = event.message
        text = " ".join(block.text for block in message.content if block.type == "text").strip() if message else ""
        if text and len(text) <= SUMMARY_MAX_LENGTH:
            return text
        logger.warning("Weekly summary for user id=%s is empty or too long (%s chars)", user_id, len(text))
    except Exception:
        logger.exception("Weekly summary LLM call failed for user id=%s", user_id)
    return week_fallback(summary)


async def weekly_summary(db: AsyncSession, user: User, now: datetime) -> list[NotificationDraft]:
    if now.weekday() != SUNDAY:
        return []
    week = now.isocalendar()
    key = f"weekly_summary:{week.year}-{week.week:02d}"
    if await NotificationRepository(db).has_key(user.id, key):
        return []
    summary = await AnalyticsService(db, user.id, DEFAULT_TIMEZONE, today=now.date()).week_summary()
    if summary is None:
        return []
    return [NotificationDraft(
        type=NotificationType.WEEKLY_SUMMARY,
        dedupe_key=key,
        title="Підсумок тижня",
        body=await write_week_summary(summary, user.id),
        data={"week_start": summary.week_start.isoformat()},
    )]


CHECKS: dict[NotificationType, Check] = {
    NotificationType.SUBSCRIPTION_PRICE: subscription_price_increases,
    NotificationType.NEW_SUBSCRIPTION: new_subscriptions,
    NotificationType.MONTH_PACE: month_pace,
    NotificationType.WEEKLY_SUMMARY: weekly_summary,
}
