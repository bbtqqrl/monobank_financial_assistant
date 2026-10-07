from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.budget import Budget
    from app.db.models.merchant_category_mappings import MerchantCategoryMapping
    from app.db.models.transaction import TransactionRaw


# What a transaction in the category means for the user's money:
#   expense  - spent (a positive amount here is a refund and offsets spending)
#   income   - received from outside
#   transfer - the user's own money moving (between own accounts, jars, cash,
#              currency exchange, loans) - neither income nor expense
#   unknown  - the fallback when nothing fits; counted by the amount's sign
CATEGORY_KINDS = ("expense", "income", "transfer", "unknown")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    # A child always has its parent's kind.
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    parent: Mapped["Category | None"] = relationship(
        back_populates="children",
        remote_side="Category.id",
    )

    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
    )

    transactions: Mapped[list["TransactionRaw"]] = relationship(
        back_populates="category",
    )

    merchant_mappings: Mapped[list["MerchantCategoryMapping"]] = relationship(
        back_populates="category",
    )

    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="category",
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('expense', 'income', 'transfer', 'unknown')",
            name="ck_categories_kind",
        ),
    )
