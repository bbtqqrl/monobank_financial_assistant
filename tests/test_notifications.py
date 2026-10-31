from datetime import datetime
from types import SimpleNamespace

from app.services.notifications import (
    KYIV_TZ,
    NotificationDraft,
    NotificationService,
    NotificationType,
    more_news,
)

NOW = datetime(2026, 11, 1, 20, 5, tzinfo=KYIV_TZ)


class FakeRepo:

    def __init__(self, pushed_today=False):
        self.rows = []
        self.pushed_today = pushed_today

    async def add_new(self, user_id, drafts):
        keys = {row.dedupe_key for row in self.rows}
        new = [SimpleNamespace(id=len(self.rows) + i + 1, pushed_at=None, **d) for i, d in enumerate(drafts)
               if d["dedupe_key"] not in keys]
        self.rows.extend(new)
        return new

    async def pushed_since(self, user_id, since):
        return self.pushed_today or any(row.pushed_at for row in self.rows)


class FakePush:

    def __init__(self, delivered=True):
        self.sent = []
        self.delivered = delivered

    async def send_visible(self, user_id, title, body, data):
        self.sent.append((title, body, data))
        return self.delivered


def draft(kind, key, body="body"):
    return NotificationDraft(type=kind, dedupe_key=key, title=kind.value, body=body)


def service(checks, repo=None, push=None):
    async def noop():
        return None

    async def get(model, user_id):
        return USER

    db = SimpleNamespace(commit=noop, rollback=noop, get=get)
    result = NotificationService(db, push=push or FakePush(), checks=checks)
    result.repo = repo or FakeRepo()
    return result


def check_returning(*drafts):
    async def check(db, user, now):
        return list(drafts)
    return check


USER = SimpleNamespace(id=5, disabled_notifications=[])


async def test_one_push_with_top_priority_and_more_news():
    push = FakePush()
    notifier = service({
        NotificationType.WEEKLY_SUMMARY: check_returning(draft(NotificationType.WEEKLY_SUMMARY, "weekly:2026-44")),
        NotificationType.SUBSCRIPTION_PRICE: check_returning(
            draft(NotificationType.SUBSCRIPTION_PRICE, "sub_price:1", "Spotify подорожчав."),
        ),
        NotificationType.MONTH_PACE: check_returning(draft(NotificationType.MONTH_PACE, "pace:2026-11")),
    }, push=push)
    top = await notifier.notify(USER, NOW)
    assert top.type == NotificationType.SUBSCRIPTION_PRICE and top.pushed_at is not None
    assert push.sent == [("subscription_price", "Spotify подорожчав. І ще 2 новини в застосунку.",
                          {"type": "notification", "notification_id": top.id, "kind": "subscription_price"})]
    assert len(notifier.repo.rows) == 3


async def test_same_notification_is_never_sent_twice():
    push = FakePush()
    notifier = service({NotificationType.INSIGHTS: check_returning(draft(NotificationType.INSIGHTS, "insights:2026-10"))},
                       push=push)
    await notifier.notify(USER, NOW)
    assert await notifier.notify(USER, NOW) is None
    assert len(push.sent) == 1


async def test_only_one_push_per_evening_rest_goes_to_inbox():
    push = FakePush()
    repo = FakeRepo(pushed_today=True)
    notifier = service({NotificationType.INSIGHTS: check_returning(draft(NotificationType.INSIGHTS, "insights:2026-10"))},
                       repo=repo, push=push)
    assert await notifier.notify(USER, NOW) is None
    assert push.sent == [] and len(repo.rows) == 1


async def test_disabled_type_and_failing_check_are_skipped():
    async def broken(db, user, now):
        raise RuntimeError("boom")

    push = FakePush()
    user = SimpleNamespace(id=5, disabled_notifications=["insights"])
    notifier = service({
        NotificationType.INSIGHTS: check_returning(draft(NotificationType.INSIGHTS, "insights:2026-10")),
        NotificationType.MONTH_PACE: broken,
        NotificationType.WEEKLY_SUMMARY: check_returning(draft(NotificationType.WEEKLY_SUMMARY, "weekly:2026-44", "Тиждень.")),
    }, push=push)
    top = await notifier.notify(user, NOW)
    assert top.type == NotificationType.WEEKLY_SUMMARY and push.sent[0][1] == "Тиждень."


async def test_failed_push_keeps_notification_unpushed():
    notifier = service({NotificationType.INSIGHTS: check_returning(draft(NotificationType.INSIGHTS, "insights:2026-10"))},
                       push=FakePush(delivered=False))
    assert await notifier.notify(USER, NOW) is None
    assert notifier.repo.rows[0].pushed_at is None


def test_more_news_plural():
    assert [more_news(n) for n in (1, 2, 5, 11, 21, 22)] == [
        "І ще 1 новина в застосунку.", "І ще 2 новини в застосунку.", "І ще 5 новин в застосунку.",
        "І ще 11 новин в застосунку.", "І ще 21 новина в застосунку.", "І ще 22 новини в застосунку.",
    ]


def subscription(id, name, amount, currency=840, previous=None, changed=None, created=NOW, cancelled_at=None,
                 user_kind=None):
    return SimpleNamespace(id=id, name=name, amount=amount, currency_code=currency, previous_amount=previous,
                           price_changed_at=changed, created_at=created, cancelled_at=cancelled_at, charges_count=2,
                           user_kind=user_kind)


def patch_subscriptions(monkeypatch, rows, first_scan):
    from app.repositories.recurring_payment import RecurringPaymentRepository
    from app.services.recurring_service import RecurringService

    async def fake_list(self, user_id, kind=None, now=None):
        assert kind == "subscription"
        return rows

    async def fake_first(self, user_id):
        return first_scan

    monkeypatch.setattr(RecurringService, "list", fake_list)
    monkeypatch.setattr(RecurringPaymentRepository, "first_created_at", fake_first)


async def test_new_subscription_skips_first_scan_old_cancelled_and_marked_by_user(monkeypatch):
    from datetime import timedelta
    from app.services.notification_checks import new_subscriptions

    first = NOW - timedelta(days=30)
    patch_subscriptions(monkeypatch, [
        subscription(1, "Claude", 2400, created=NOW - timedelta(hours=3)),
        subscription(2, "Friendly Share", 12900, currency=980, created=first),
        subscription(3, "Old", 999, created=NOW - timedelta(days=10)),
        subscription(4, "Cancelled", 999, created=NOW - timedelta(hours=3), cancelled_at=1),
        subscription(5, "Marked", 999, created=NOW - timedelta(hours=3), user_kind="subscription"),
    ], first)
    drafts = await new_subscriptions(None, USER, NOW)
    assert [(d.dedupe_key, d.body, d.data) for d in drafts] == [
        ("new_subscription:1", "Claude: 24 $ щомісяця, списується вже другий місяць. Додали до твоїх підписок.", {"recurring_id": 1}),
    ]


async def test_price_increase_only_recent_and_up(monkeypatch):
    from datetime import timedelta
    from app.services.notification_checks import subscription_price_increases

    recent = int((NOW - timedelta(days=2)).timestamp())
    old = int((NOW - timedelta(days=20)).timestamp())
    patch_subscriptions(monkeypatch, [
        subscription(1, "Spotify", 599, previous=499, changed=recent),
        subscription(2, "Netflix", 25000, currency=980, previous=32000, changed=recent),
        subscription(3, "Apple", 19900, currency=980, previous=14900, changed=old),
        subscription(4, "Claude", 2400),
        subscription(5, "Google One", 10300, currency=980, previous=10000, changed=recent),
    ], NOW - timedelta(days=60))
    drafts = await subscription_price_increases(None, USER, NOW)
    assert [(d.dedupe_key, d.body) for d in drafts] == [
        (f"subscription_price:1:{recent}", "Spotify: було 4,99 $, тепер 5,99 $ (+20%)."),
    ]


def test_format_money():
    from app.core.currencies import format_money

    assert format_money(12900, 980) == "129 ₴"
    assert format_money(-123456, 980) == "1 234,56 ₴"
    assert format_money(499, 840) == "4,99 $"
    assert format_money(1000, 985) == "10 zł"
    assert format_money(1000, 203) == "10 CZK"


def patch_pace(monkeypatch, pace):
    from app.services.analytics_service import AnalyticsService

    async def fake_pace(self):
        return pace

    monkeypatch.setattr(AnalyticsService, "month_pace", fake_pace)


def pace(spent, usual, top=None, diff=0):
    from app.schemas.analytics import CategoryRef, MonthPace

    category = CategoryRef(id=13, name=top, slug="kafe") if top else None
    return MonthPace(month="2026-11", day=15, spent=spent, usual=usual, months_used=6, top_category=category,
                     top_category_diff=diff)


async def test_month_pace_texts(monkeypatch):
    from app.services.notification_checks import month_pace

    on_15th = datetime(2026, 11, 15, 20, 5, tzinfo=KYIV_TZ)
    cases = [
        (pace(880000, 1000000), "Ти молодець: з 1 по 15 листопада витрачено 8 800 ₴, це на 12% менше, ніж зазвичай."),
        (pace(1030000, 1000000), "З 1 по 15 листопада витрачено 10 300 ₴. Йдеш у звичному темпі."),
        (pace(1180000, 1000000, "Кафе та ресторани", 120000),
         "З 1 по 15 листопада витрачено 11 800 ₴, це на 18% більше, ніж зазвичай. "
         "Найбільше зросла категорія «Кафе та ресторани»: +1 200 ₴."),
    ]
    for result, body in cases:
        patch_pace(monkeypatch, result)
        [notification] = await month_pace(None, USER, on_15th)
        assert notification.body == body and notification.dedupe_key == "month_pace:2026-11"


async def test_month_pace_only_mid_month_and_with_history(monkeypatch):
    from app.services.notification_checks import month_pace

    patch_pace(monkeypatch, pace(1000, 1000))
    assert await month_pace(None, USER, datetime(2026, 11, 14, 20, tzinfo=KYIV_TZ)) == []
    assert await month_pace(None, USER, datetime(2026, 11, 21, 20, tzinfo=KYIV_TZ)) == []
    assert len(await month_pace(None, USER, datetime(2026, 11, 18, 20, tzinfo=KYIV_TZ))) == 1
    patch_pace(monkeypatch, None)
    assert await month_pace(None, USER, datetime(2026, 11, 15, 20, tzinfo=KYIV_TZ)) == []


def week(usual=500000, categories=True, biggest=True):
    from datetime import date
    from app.schemas.analytics import WeekCategory, WeekPurchase, WeekSummary

    return WeekSummary(
        week_start=date(2026, 10, 26), week_end=date(2026, 11, 1), spent=420037, usual=usual, count=34,
        categories=[WeekCategory(name="Продукти", spent=150000, usual=120000 if usual else None)] if categories else [],
        biggest=WeekPurchase(description="Rozetka", amount=180000, category="Техніка та електроніка") if biggest else None,
    )


def test_week_facts_have_ready_numbers():
    from app.services.notification_checks import week_facts

    assert week_facts(week()) == (
        "Тиждень: 26 жовтня – 1 листопада\n"
        "Витрачено: 4 200 ₴, покупок: 34\n"
        "Звичайний тиждень: 5 000 ₴, різниця -16%\n"
        "Категорія «Продукти»: 1 500 ₴, зазвичай 1 200 ₴ на тиждень\n"
        "Найбільша покупка: Rozetka — 1 800 ₴ («Техніка та електроніка»)"
    )
    assert "історії для порівняння ще мало" in week_facts(week(usual=None, categories=False, biggest=False))
    rare = week()
    rare.categories[0].usual = 3500
    assert "Категорія «Продукти»: 1 500 ₴, зазвичай на це майже не витрачається" in week_facts(rare)


class FakeLLM:

    def __init__(self, text=None, error=None):
        self.text, self.error = text, error
        self.calls = []

    async def stream(self, **kwargs):
        from app.services.llm.client import Completed

        self.calls.append(kwargs)
        if self.error:
            raise self.error
        yield Completed(SimpleNamespace(content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=self.text)]))


async def test_week_summary_uses_llm_text_or_falls_back():
    from app.services.notification_checks import write_week_summary

    llm = FakeLLM(" За тиждень пішло 4 200 ₴ — на 16% менше, ніж зазвичай. ")
    assert await write_week_summary(week(), 5, llm) == "За тиждень пішло 4 200 ₴ — на 16% менше, ніж зазвичай."
    assert llm.calls[0]["purpose"] == "weekly_summary" and llm.calls[0]["user_id"] == 5

    fallback = "За тиждень витрачено 4 200 ₴, на 16% менше, ніж зазвичай. Найбільше пішло на «Продукти»: 1 500 ₴."
    assert await write_week_summary(week(), 5, FakeLLM(error=RuntimeError("down"))) == fallback
    assert await write_week_summary(week(), 5, FakeLLM("x" * 301)) == fallback
    assert await write_week_summary(week(usual=None), 5, FakeLLM("")) == (
        "За тиждень витрачено 4 200 ₴. Найбільше пішло на «Продукти»: 1 500 ₴."
    )


async def test_weekly_summary_only_on_sunday_and_once(monkeypatch):
    from app.repositories.notification import NotificationRepository
    from app.services import notification_checks
    from app.services.analytics_service import AnalyticsService

    calls = []

    async def fake_summary(self):
        calls.append(self.today)
        return week()

    async def fake_write(summary, user_id, llm=None):
        return "Текст."

    existing = set()

    async def has_key(self, user_id, key):
        return key in existing

    monkeypatch.setattr(AnalyticsService, "week_summary", fake_summary)
    monkeypatch.setattr(notification_checks, "write_week_summary", fake_write)
    monkeypatch.setattr(NotificationRepository, "has_key", has_key)

    async def noop():
        return None

    db = SimpleNamespace(commit=noop)
    assert await notification_checks.weekly_summary(db, USER, datetime(2026, 10, 31, 20, tzinfo=KYIV_TZ)) == []
    [draft] = await notification_checks.weekly_summary(db, USER, NOW)
    assert (draft.dedupe_key, draft.body, draft.data) == ("weekly_summary:2026-44", "Текст.", {"week_start": "2026-10-26"})
    existing.add("weekly_summary:2026-44")
    assert await notification_checks.weekly_summary(db, USER, NOW) == []
    assert len(calls) == 1


def insight(category_id, name, current, diff, streak=3):
    from app.schemas.analytics import Insight, InsightAction

    return Insight(
        type="category_growth_streak", category_id=category_id, category_name=name,
        title=f"{name} зростає третій місяць поспіль", text="", streak_months=streak, current=current,
        baseline=current - diff, diff=diff, action=InsightAction(type="open_transactions", category_id=category_id, month="2026-10"),
    )


async def test_monthly_insights_for_previous_month(monkeypatch):
    from app.schemas.analytics import InsightsResponse
    from app.services.analytics_service import AnalyticsService
    from app.services.notification_checks import monthly_insights

    asked = []
    items = [insight(13, "Кафе та ресторани", 520000, 180000), insight(1, "Продукти", 900000, 50000)]

    async def fake_insights(self, month):
        asked.append(month)
        return InsightsResponse(month="2026-10", items=items)

    monkeypatch.setattr(AnalyticsService, "insights", fake_insights)
    [draft] = await monthly_insights(None, USER, NOW)
    assert asked == [NOW.date().replace(month=10)]
    assert draft.title == "Кафе та ресторани зростає третій місяць поспіль"
    assert draft.body == (
        "У жовтні на «Кафе та ресторани» пішло 5 200 ₴, на 1 800 ₴ більше, ніж зазвичай. Ще 1 категорія теж росте, деталі в застосунку."
    )
    assert (draft.dedupe_key, draft.data) == ("insights:2026-10", {"month": "2026-10", "category_id": 13})

    assert await monthly_insights(None, USER, datetime(2026, 11, 6, 20, tzinfo=KYIV_TZ)) == []
    items.clear()
    assert await monthly_insights(None, USER, NOW) == []


async def test_insights_in_january_look_at_december(monkeypatch):
    from app.schemas.analytics import InsightsResponse
    from app.services.analytics_service import AnalyticsService
    from app.services.notification_checks import monthly_insights

    async def fake_insights(self, month):
        return InsightsResponse(month="2026-12", items=[insight(1, "Продукти", 900000, 50000)])

    monkeypatch.setattr(AnalyticsService, "insights", fake_insights)
    [draft] = await monthly_insights(None, USER, datetime(2027, 1, 2, 20, tzinfo=KYIV_TZ))
    assert draft.dedupe_key == "insights:2026-12" and draft.body.startswith("У грудні")
