from contextlib import asynccontextmanager
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

    @asynccontextmanager
    async def begin_nested():
        yield

    db = SimpleNamespace(commit=noop, begin_nested=begin_nested)
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
