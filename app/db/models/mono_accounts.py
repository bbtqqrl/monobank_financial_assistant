from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class MonoAccount(Base):
    __tablename__ = "mono_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    mono_account_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
    )

    send_id: Mapped[str | None] = mapped_column(String, nullable=True)
    currency_code: Mapped[int] = mapped_column(Integer)
    cashback_type: Mapped[str | None] = mapped_column(String, nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    credit_limit: Mapped[int] = mapped_column(BigInteger, default=0)
    masked_pan: Mapped[str | None] = mapped_column(String, nullable=True)
    account_type: Mapped[str] = mapped_column(String)
    iban: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)