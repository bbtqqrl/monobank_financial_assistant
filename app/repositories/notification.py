from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.db.models.user import User


class NotificationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_new(self, user_id: int, drafts: list[dict]) -> list[Notification]:
        if not drafts:
            return []
        result = await self.db.execute(
            pg_insert(Notification)
            .values([{"user_id": user_id, **draft} for draft in drafts])
            .on_conflict_do_nothing(constraint="uq_notifications_user_dedupe_key")
            .returning(Notification)
        )
        return list(result.scalars().all())

    async def pushed_since(self, user_id: int, since: datetime) -> bool:
        result = await self.db.execute(
            select(Notification.id).where(Notification.user_id == user_id, Notification.pushed_at >= since).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def has_key(self, user_id: int, dedupe_key: str) -> bool:
        result = await self.db.execute(
            select(Notification.id).where(Notification.user_id == user_id, Notification.dedupe_key == dedupe_key)
        )
        return result.scalar_one_or_none() is not None

    async def list_for_user(self, user_id: int, limit: int, offset: int) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return result.scalar_one()

    async def mark_read(self, user_id: int, notification_id: int | None = None) -> int:
        statement = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        if notification_id is not None:
            statement = statement.where(Notification.id == notification_id)
        result = await self.db.execute(statement.values(read_at=func.now()))
        return result.rowcount

    async def exists(self, user_id: int, notification_id: int) -> bool:
        result = await self.db.execute(
            select(Notification.id).where(Notification.user_id == user_id, Notification.id == notification_id)
        )
        return result.scalar_one_or_none() is not None

    async def active_user_ids(self) -> list[int]:
        result = await self.db.execute(select(User.id).where(User.is_active.is_(True)).order_by(User.id))
        return list(result.scalars().all())
