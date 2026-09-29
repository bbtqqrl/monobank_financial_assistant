from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.categories import Category
    from app.db.models.user import User


class Budget(Base):
    __tablename__ = "budgets"

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

    # Monthly limit. What's been spent against it isn't stored - it's summed
    # from transactions on read (see BudgetRepository.spent_by_category), so
    # it can't drift on re-categorization, hold settlement or backfill.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship(back_populates="budgets")
    category: Mapped["Category"] = relationship(back_populates="budgets")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category_budget"),
    )
