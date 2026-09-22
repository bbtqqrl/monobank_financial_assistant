from pydantic import BaseModel, ConfigDict, Field


class CategoryBrief(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class TransactionListItem(BaseModel):
    id: int
    source: str
    time: int
    description: str
    amount: int
    operation_amount: int | None
    currency_code: int
    mcc: int | None
    account_id: int | None
    jar_id: int | None
    category: CategoryBrief | None
    category_source: str | None


class TransactionDetail(TransactionListItem):
    balance: int | None
    comment: str | None
    counter_name: str | None
    counter_edrpou: str | None
    counter_iban: str | None


class TransactionListResponse(BaseModel):
    items: list[TransactionListItem]
    page: int
    limit: int
    total: int


class UpdateTransactionCategoryRequest(BaseModel):
    category_id: int


class CreateTransactionRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: int = Field(description="In minor units (kopecks). Negative = expense, positive = income.")
    currency_code: int = 980
    category_id: int | None = None
    account_id: int | None = None
    jar_id: int | None = None
    time: int | None = Field(default=None, description="Unix seconds; defaults to now if omitted")
    comment: str | None = Field(default=None, max_length=500)
