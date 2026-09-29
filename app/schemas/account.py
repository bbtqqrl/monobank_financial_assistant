from pydantic import BaseModel, ConfigDict


class AccountResponse(BaseModel):
    id: int
    mono_account_id: str
    account_type: str
    currency_code: int
    balance: int
    credit_limit: int
    masked_pan: str | None
    iban: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class JarResponse(BaseModel):
    id: int
    mono_jar_id: str
    title: str
    description: str | None
    currency_code: int
    balance: int
    goal: int | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
