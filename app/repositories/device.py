from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device


class DeviceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, user_id: int, push_token: str, platform: str) -> None:
        values = {"user_id": user_id, "platform": platform}
        await self.db.execute(
            pg_insert(Device)
            .values(push_token=push_token, **values)
            .on_conflict_do_update(index_elements=[Device.push_token], set_={**values, "updated_at": func.now()})
        )

    async def list_tokens(self, user_id: int) -> list[str]:
        result = await self.db.execute(select(Device.push_token).where(Device.user_id == user_id))
        return list(result.scalars().all())

    async def has_any(self, user_id: int) -> bool:
        result = await self.db.execute(select(Device.id).where(Device.user_id == user_id).limit(1))
        return result.scalar_one_or_none() is not None

    async def delete_for_user(self, user_id: int, push_token: str) -> None:
        await self.db.execute(delete(Device).where(Device.user_id == user_id, Device.push_token == push_token))

    async def delete_tokens(self, push_tokens: list[str]) -> None:
        await self.db.execute(delete(Device).where(Device.push_token.in_(push_tokens)))
