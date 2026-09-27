from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.categories import Category
    from app.db.models.transaction import TransactionRaw
    from app.db.models.user import User

class MerchantCategoryMapping(Base):
    __tablename__ = "merchant_category_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    merchant_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mcc: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="AI",
    )

    # Set when `source` traces back to an AI guess (confident or not), so a
    # transaction picked up via this mapping can still be flagged for review
    # instead of silently inheriting a shaky guess. Cleared once a human
    # confirms the mapping (see update_category).
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="merchant_mappings",
    )

    category: Mapped["Category"] = relationship(
        back_populates="merchant_mappings",
    )

    transactions: Mapped[list["TransactionRaw"]] = relationship(
        back_populates="merchant_mapping",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "merchant_key",
            "mcc",
            name="uq_user_merchant_mcc",
        ),
    )