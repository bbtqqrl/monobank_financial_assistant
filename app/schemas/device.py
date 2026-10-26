from typing import Literal

from pydantic import BaseModel, Field

PUSH_TOKEN_PATTERN = r"^Expo(nent)?PushToken\[[^\]]+\]$"


class RegisterDeviceRequest(BaseModel):
    push_token: str = Field(max_length=255, pattern=PUSH_TOKEN_PATTERN)
    platform: Literal["ios", "android"]
