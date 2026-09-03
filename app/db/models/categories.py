from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models import MerchantCategoryMapping
from app.db.models import TransactionCategory


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

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    transaction_categories: Mapped[list["TransactionCategory"]] = relationship(
        back_populates="category",
    )

    merchant_mappings: Mapped[list["MerchantCategoryMapping"]] = relationship(
        back_populates="category",
    )