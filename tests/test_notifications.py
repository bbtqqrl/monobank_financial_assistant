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


def subscription(id, name, amount, currency=840, previous=None, changed=None, created=NOW, cancelled_at=None):
    return SimpleNamespace(id=id, name=name, amount=amount, currency_code=currency, previous_amount=previous,
                           price_changed_at=changed, created_at=created, cancelled_at=cancelled_at)


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


async def test_new_subscription_skips_first_scan_old_and_cancelled(monkeypatch):
    from datetime import timedelta
    from app.services.notification_checks import new_subscriptions

    first = NOW - timedelta(days=30)
    patch_subscriptions(monkeypatch, [
        subscription(1, "Claude", 2400, created=NOW - timedelta(hours=3)),
        subscription(2, "Friendly Share", 12900, currency=980, created=first),
        subscription(3, "Old", 999, created=NOW - timedelta(days=10)),
        subscription(4, "Cancelled", 999, created=NOW - timedelta(hours=3), cancelled_at=1),
    ], first)
    drafts = await new_subscriptions(None, USER, NOW)
    assert [(d.dedupe_key, d.body, d.data) for d in drafts] == [
        ("new_subscription:1", "Claude: 24 $ щомісяця. Додали її до твоїх підписок.", {"recurring_id": 1}),
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
