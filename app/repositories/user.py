from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from db.models.user import User

class UserRepository:
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update(self, telegram_id: int, client_id: str, token: str) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        
        if user:
            user.mono_token = token
        else:
            user = User(
                mono_client_id=client_id,
                telegram_id=telegram_id,
                mono_token=token,
            )
            self.db.add(user)
            await self.db.flush()
        
        return user