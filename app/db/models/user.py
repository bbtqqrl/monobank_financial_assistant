from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedString
from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.merchant_category_mappings import MerchantCategoryMapping
    from app.db.models.mono_accounts import MonoAccount
    from app.db.models.mono_jars import MonoJar
    from app.db.models.refresh_token import RefreshToken
    from app.db.models.transaction import TransactionRaw

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    mono_client_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    mono_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)

    accounts: Mapped[list["MonoAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    jars: Mapped[list["MonoJar"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    transactions: Mapped[list["TransactionRaw"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    merchant_mappings: Mapped[list["MerchantCategoryMapping"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
