from pydantic import BaseModel, ConfigDict, Field


class CategoryBrief(BaseModel):
    id: int
    name: str
    slug: str
    kind: str

    model_config = ConfigDict(from_attributes=True)


class TransactionListItem(BaseModel):
    id: int
    source: str
    time: int
    description: str
    amount: int
    account_currency_code: int
    operation_amount: int | None
    currency_code: int
    mcc: int | None
    account_id: int | None
    jar_id: int | None
    transfer_pair_id: int | None
    category: CategoryBrief | None
    category_source: str | None
    category_confidence: float | None


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
    currency_code: int | None = Field(
        default=None,
        description="ISO 4217 numeric. Taken from the account or jar when one is given; defaults to 980 (UAH) otherwise.",
    )
    # Required: a manual transaction is never seen by the AI or the sweeper,
    # so without a category here it would stay uncategorized forever.
    category_id: int
    account_id: int | None = None
    jar_id: int | None = None
    time: int | None = Field(default=None, description="Unix seconds; defaults to now if omitted")
    comment: str | None = Field(default=None, max_length=500)


class UpdateManualTransactionRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    amount: int | None = Field(default=None, description="In minor units (kopecks). Negative = expense, positive = income.")
    category_id: int | None = None
    time: int | None = None
    comment: str | None = Field(default=None, max_length=500)
