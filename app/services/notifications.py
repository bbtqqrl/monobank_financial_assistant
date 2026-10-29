import asyncio
import logging
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.db.models.user import User
from app.db.session import SessionLocal
from app.repositories.notification import NotificationRepository
from app.repositories.user import UserRepository
from app.schemas.notification import NotificationType
from app.services.errors import NotFoundError
from app.services.notification_checks import CHECKS, Check, NotificationDraft
from app.services.push import PushService

logger = logging.getLogger(__name__)

KYIV_TZ = ZoneInfo("Europe/Kyiv")
SEND_HOUR = 20
LAST_SEND_HOUR = 21
CHECK_INTERVAL_SECONDS = 5 * 60
NOTIFICATION_PUSH = "notification"
PRIORITY = list(NotificationType)


def more_news(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        word = "новина"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "новини"
    else:
        word = "новин"
    return f"І ще {count} {word} в застосунку."


class NotificationService:

    def __init__(self, db: AsyncSession, push: PushService | None = None, checks: dict[NotificationType, Check] | None = None):
        self.db = db
        self.repo = NotificationRepository(db)
        self.push = push or PushService(db)
        self.checks = CHECKS if checks is None else checks

    async def notify(self, user: User, now: datetime) -> Notification | None:
        user_id = user.id
        disabled = set(user.disabled_notifications)
        drafts: list[NotificationDraft] = []
        for kind, check in self.checks.items():
            if kind in disabled:
                continue
            try:
                drafts.extend(await check(self.db, user, now))
            except Exception:
                logger.exception("Notification check %s failed for user id=%s", kind, user_id)
                await self.db.rollback()
                user = await self.db.get(User, user_id)
        created = await self.repo.add_new(user_id, [
            {"type": d.type, "dedupe_key": d.dedupe_key, "title": d.title, "body": d.body, "data": d.data}
            for d in drafts
        ])
        await self.db.commit()
        if not created:
            return None
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        if await self.repo.pushed_since(user_id, start_of_day):
            return None
        created.sort(key=lambda notification: PRIORITY.index(notification.type))
        top = created[0]
        body = top.body if len(created) == 1 else f"{top.body} {more_news(len(created) - 1)}"
        data = {"type": NOTIFICATION_PUSH, "notification_id": top.id, "kind": top.type, **top.data}
        if await self.push.send_visible(user_id, top.title, body, data):
            top.pushed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return top
        return None

    async def list(self, user_id: int, limit: int, offset: int) -> tuple[int, list[Notification]]:
        return await self.repo.unread_count(user_id), await self.repo.list_for_user(user_id, limit, offset)

    async def mark_read(self, user_id: int, notification_id: int | None = None) -> None:
        if notification_id is not None and not await self.repo.exists(user_id, notification_id):
            raise NotFoundError("Notification not found")
        await self.repo.mark_read(user_id, notification_id)
        await self.db.commit()

    async def set_enabled(self, user: User, changes: dict[NotificationType, bool]) -> None:
        disabled = set(user.disabled_notifications)
        for kind, enabled in changes.items():
            (disabled.discard if enabled else disabled.add)(kind.value)
        user.disabled_notifications = sorted(disabled)
        await self.db.commit()


async def send_evening_notifications(now: datetime) -> None:
    async with SessionLocal() as db:
        user_ids = await NotificationRepository(db).active_user_ids()
    pushed = 0
    for user_id in user_ids:
        async with SessionLocal() as db:
            try:
                user = await UserRepository(db).get_by_id(user_id)
                if user is not None and await NotificationService(db).notify(user, now):
                    pushed += 1
            except Exception:
                logger.exception("Evening notifications failed for user id=%s", user_id)
    logger.info("Evening notifications: %s user(s), %s push(es)", len(user_ids), pushed)


async def run_notifier_forever() -> None:
    last_run: date | None = None
    while True:
        now = datetime.now(KYIV_TZ)
        if SEND_HOUR <= now.hour <= LAST_SEND_HOUR and last_run != now.date():
            last_run = now.date()
            try:
                await send_evening_notifications(now)
            except Exception:
                logger.exception("Evening notifications failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
