from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.categories import Category
from app.db.models.merchant_category_mappings import MerchantCategoryMapping
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.category import CategoryRepository
from app.repositories.merchant_mapping import MerchantCategoryMappingRepository
from app.schemas.merchant_mapping import MerchantMappingResponse, UpdateMerchantMappingRequest
from app.schemas.transaction import CategoryBrief

router = APIRouter(prefix="/merchant-mappings", tags=["Merchant Mappings"])


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


@router.get("", response_model=list[MerchantMappingResponse])
async def list_merchant_mappings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MerchantCategoryMappingRepository(db)
    rows = await repo.list_for_user(current_user.id)
    return [_to_response(mapping, category) for mapping, category in rows]


@router.patch("/{mapping_id}", response_model=MerchantMappingResponse)
async def update_merchant_mapping(
    mapping_id: int,
    data: UpdateMerchantMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MerchantCategoryMappingRepository(db)
    mapping = await repo.get_by_id_for_user(mapping_id, current_user.id)
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")

    category = await CategoryRepository(db).get_selectable_by_id(data.category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or not selectable")

    repo.update_category(mapping, category.id)
    await db.commit()

    return _to_response(mapping, category)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MerchantCategoryMappingRepository(db)
    mapping = await repo.get_by_id_for_user(mapping_id, current_user.id)
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")

    repo.deactivate(mapping)
    await db.commit()
