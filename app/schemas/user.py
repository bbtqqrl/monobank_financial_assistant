from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: int
    mono_client_id: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

