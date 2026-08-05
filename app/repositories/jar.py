from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from db.models.user import User
from db.models.mono_jars import MonoJar

class JarRepository:
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_mono_id(self, mono_jar_id: str) -> Optional[MonoJar]:
        result = await self.db.execute(
            select(MonoJar).where(MonoJar.mono_jar_id == mono_jar_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, user: User, jar: dict) -> None:
        self.db.add(
            MonoJar(
                user_id=user.id,
                mono_jar_id=jar["id"],
                title=jar["title"],
                balance=jar.get("balance", 0),
                goal=jar.get("goal"),
                description=jar.get("description"),
                currency_code=jar["currencyCode"],
            )
        )
    
    async def update(self, jar_db: MonoJar, jar: dict) -> None:
        jar_db.title = jar["title"]
        jar_db.balance = jar.get("balance", 0)
        jar_db.goal = jar.get("goal")
        jar_db.description = jar.get("description")
        jar_db.currency_code = jar["currencyCode"]
        jar_db.is_active = True