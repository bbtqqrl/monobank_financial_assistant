from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.categories import Category


class RecurringPayment(Base):
    __tablename__ = "recurring_payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    merchant_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mcc: Mapped[int | None] = mapped_column(Integer, nullable=True)

    kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    declined_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cancelled_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    currency_code: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_uah: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    first_charge_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_charge_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charges_count: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    price_changed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    category: Mapped["Category | None"] = relationship(lazy="selectin")
