from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcc_place_type import MccPlaceType


class MccPlaceTypeRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, mcc: int) -> MccPlaceType | None:
        return await self.db.get(MccPlaceType, mcc)
