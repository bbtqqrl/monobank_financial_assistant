from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_usage import LLMUsage


class LLMUsageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    def add(self, usage: LLMUsage) -> None:
        self.db.add(usage)
