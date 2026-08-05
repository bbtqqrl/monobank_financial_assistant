from pydantic import BaseModel
from datetime import datetime


class TransactionResponse(BaseModel):
    id: int
    description: str
    amount: int
    currency_code: int
    mcc: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }