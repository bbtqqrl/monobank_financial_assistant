from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    mono_client_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    mono_token: Mapped[str] = mapped_column(String, nullable=True)