from pydantic import BaseModel

from app.schemas.transaction import CategoryBrief


class MerchantMappingResponse(BaseModel):
    id: int
    merchant_key: str
    mcc: int
    source: str
    is_active: bool
    category: CategoryBrief


class UpdateMerchantMappingRequest(BaseModel):
    category_id: int
