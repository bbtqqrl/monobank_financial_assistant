from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransactionRaw(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("mono_accounts.id", ondelete="CASCADE"),
        index=True,
    )

    mono_transaction_id: Mapped[str] = mapped_column(String,unique=True,index=True,)

    time: Mapped[int] = mapped_column(BigInteger, index=True)
    description: Mapped[str] = mapped_column(Text)

    mcc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_mcc: Mapped[int | None] = mapped_column(Integer, nullable=True)

    hold: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    operation_amount: Mapped[int | None] = mapped_column(BigInteger,nullable=True,)
    currency_code: Mapped[int] = mapped_column(Integer)
    commission_rate: Mapped[int | None] = mapped_column(BigInteger,nullable=True,)
    cashback_amount: Mapped[int | None] = mapped_column(BigInteger,nullable=True,)

    balance: Mapped[int | None] = mapped_column(BigInteger,nullable=True,)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(String, nullable=True)
    counter_edrpou: Mapped[str | None] = mapped_column(String, nullable=True)
    counter_iban: Mapped[str | None] = mapped_column(String, nullable=True)
    counter_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON)