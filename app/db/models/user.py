from typing import TYPE_CHECKING

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.mono_accounts import MonoAccount
    from app.db.models.mono_jars import MonoJar
    from app.db.models.transaction import TransactionRaw

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    mono_client_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    mono_token: Mapped[str] = mapped_column(String, nullable=True)

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