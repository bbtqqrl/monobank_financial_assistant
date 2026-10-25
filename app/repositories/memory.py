from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import Memory


class MemoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: int) -> list[Memory]:
        result = await self.db.execute(
            select(Memory).where(Memory.user_id == user_id).order_by(Memory.id)
        )
        return list(result.scalars().all())

    async def get_for_user(self, memory_id: int, user_id: int) -> Memory | None:
        result = await self.db.execute(
            select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def count_for_user(self, user_id: int) -> int:
        result = await self.db.execute(select(func.count(Memory.id)).where(Memory.user_id == user_id))
        return result.scalar_one()

    async def create(self, user_id: int, text: str, conversation_id: int | None = None) -> Memory:
        memory = Memory(user_id=user_id, text=text, conversation_id=conversation_id)
        self.db.add(memory)
        await self.db.flush()
        return memory

    @staticmethod
    def update(memory: Memory, text: str) -> None:
        memory.text = text
        memory.updated_at = func.now()

    async def delete(self, memory: Memory) -> None:
        await self.db.delete(memory)
