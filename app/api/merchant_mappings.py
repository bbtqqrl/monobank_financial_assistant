from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.merchant_mapping import MerchantMappingResponse, UpdateMerchantMappingRequest
from app.services.merchant_mapping_service import MerchantMappingService

router = APIRouter(prefix="/merchant-mappings", tags=["Merchant Mappings"])


@router.get("", response_model=list[MerchantMappingResponse])
async def list_merchant_mappings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MerchantMappingService(db, current_user.id).list_all()


@router.patch("/{mapping_id}", response_model=MerchantMappingResponse)
async def update_merchant_mapping(
    mapping_id: int,
    data: UpdateMerchantMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MerchantMappingService(db, current_user.id).update_category(mapping_id, data.category_id)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await MerchantMappingService(db, current_user.id).deactivate(mapping_id)
