from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.merchant_category_mappings import MerchantCategoryMapping
from app.repositories.category import CategoryRepository
from app.repositories.merchant_mapping import MerchantCategoryMappingRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.merchant_mapping import MerchantMappingResponse
from app.schemas.transaction import CategoryBrief
from app.services.errors import InvalidRequestError, NotFoundError


class MerchantMappingService:

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.mappings = MerchantCategoryMappingRepository(db)
        self.categories = CategoryRepository(db)
        self.transactions = TransactionRepository(db)

    async def list_all(self) -> list[MerchantMappingResponse]:
        rows = await self.mappings.list_for_user(self.user_id)
        return [self._to_response(mapping, category) for mapping, category in rows]

    async def update_category(self, mapping_id: int, category_id: int) -> MerchantMappingResponse:
        mapping = await self._get(mapping_id)
        category = await self.categories.get_selectable_by_id(category_id)
        if category is None:
            raise InvalidRequestError("Category not found or not selectable")

        self.mappings.update_category(mapping, category.id)
        await self.transactions.apply_mapping_category(mapping.id, category.id)
        await self.db.commit()
        return self._to_response(mapping, category)

    async def deactivate(self, mapping_id: int) -> None:
        mapping = await self._get(mapping_id)
        self.mappings.deactivate(mapping)
        await self.db.commit()

    async def _get(self, mapping_id: int) -> MerchantCategoryMapping:
        mapping = await self.mappings.get_by_id_for_user(mapping_id, self.user_id)
        if mapping is None:
            raise NotFoundError("Mapping not found")
        return mapping

    @staticmethod
    def _to_response(mapping: MerchantCategoryMapping, category: Category) -> MerchantMappingResponse:
        return MerchantMappingResponse(
            id=mapping.id,
            merchant_key=mapping.merchant_key,
            mcc=mapping.mcc,
            source=mapping.source,
            confidence=mapping.confidence,
            is_active=mapping.is_active,
            category=CategoryBrief.model_validate(category),
        )
