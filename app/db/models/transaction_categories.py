from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.merchant_category_mappings import MerchantCategoryMapping
    from app.db.models.transaction import TransactionRaw

class TransactionCategory(Base):
    __tablename__ = "transaction_categories"

    id: Mapped[int] = mapped_column(primary_key=True)

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    merchant_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "merchant_category_mappings.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    merchant_mapping: Mapped["MerchantCategoryMapping | None"] = relationship(
        back_populates="transaction_categories",
    )

    transaction: Mapped["TransactionRaw"] = relationship(
        back_populates="category",
    )

