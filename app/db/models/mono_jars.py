from sqlalchemy import ForeignKey, Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class MonoJar(Base):
    __tablename__ = "mono_jars"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    mono_jar_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    goal: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    currency_code: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)