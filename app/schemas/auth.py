from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

# Emails are stored and looked up lower-case, so "A@x.com" and "a@x.com"
# are the same account.
NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]


class RegisterRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: NormalizedEmail
    # Same cap as on register: keeps an oversized body from going to argon2.
    password: str = Field(max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
