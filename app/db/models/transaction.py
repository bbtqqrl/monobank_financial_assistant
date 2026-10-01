from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.categories import Category
    from app.db.models.merchant_category_mappings import MerchantCategoryMapping
    from app.db.models.mono_accounts import MonoAccount
    from app.db.models.mono_jars import MonoJar
    from app.db.models.user import User

class TransactionRaw(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("mono_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    jar_id: Mapped[int | None] = mapped_column(
        ForeignKey("mono_jars.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    transfer_pair_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    mono_transaction_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)

    source: Mapped[str] = mapped_column(String(20), nullable=False, default="monobank")

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    category_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    merchant_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchant_category_mappings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # When the row landed in our DB (`time` is the bank's timestamp). Lets the
    # categorization sweeper tell a transaction whose in-flight categorization
    # was lost to a restart from one that is still being worked on.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="transactions",
    )

    account: Mapped["MonoAccount | None"] = relationship(
        back_populates="transactions",
    )

    jar: Mapped["MonoJar | None"] = relationship(
        back_populates="transactions",
    )

    category: Mapped["Category | None"] = relationship(
        back_populates="transactions",
    )

    merchant_mapping: Mapped["MerchantCategoryMapping | None"] = relationship(
        back_populates="transactions",
    )