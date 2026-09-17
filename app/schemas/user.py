from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    mono_client_id: str | None = None

    model_config = ConfigDict(from_attributes=True)
