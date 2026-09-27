from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import date
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

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    current_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Start of the calendar month `current_amount` covers. Reset lazily
    # (see BudgetRepository) whenever the budget is read/updated in a later
    # month, rather than via a scheduled job.
    period_start: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship(back_populates="budgets")
    category: Mapped["Category"] = relationship(back_populates="budgets")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category_budget"),
    )
