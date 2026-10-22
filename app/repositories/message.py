from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.message import Message


class MessageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def history(self, conversation_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return [{"role": role, "content": content} for role, content in result.all()]

    async def add(self, conversation_id: int, role: str, content: list[dict]) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_for_conversation(self, conversation_id: int) -> list[Message]:
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        )
        return list(result.scalars().all())

    async def count_user_texts_since(self, user_id: int, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.user_id == user_id,
                Message.role == "user",
                Message.created_at >= since,
                Message.content.contains([{"type": "text"}]),
            )
        )
        return result.scalar_one()
