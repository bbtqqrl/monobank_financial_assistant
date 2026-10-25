from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pending_action import PendingAction


class PendingActionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        conversation_id: int,
        tool_use_id: str | None,
        action_type: str,
        payload: dict,
        preview: dict,
        expires_at: datetime,
    ) -> PendingAction:
        action = PendingAction(
            user_id=user_id,
            conversation_id=conversation_id,
            tool_use_id=tool_use_id,
            action_type=action_type,
            payload=payload,
            preview=preview,
            expires_at=expires_at,
        )
        self.db.add(action)
        await self.db.flush()
        return action

    async def get_for_user(self, action_id: int, user_id: int) -> PendingAction | None:
        result = await self.db.execute(
            select(PendingAction).where(PendingAction.id == action_id, PendingAction.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_conversation(self, conversation_id: int) -> list[PendingAction]:
        result = await self.db.execute(
            select(PendingAction).where(PendingAction.conversation_id == conversation_id).order_by(PendingAction.id)
        )
        return list(result.scalars().all())

    @staticmethod
    def resolve(action: PendingAction, status: str, result: dict | None = None, error: str | None = None) -> None:
        action.status = status
        action.result = result
        action.error = error
        action.resolved_at = func.now()
