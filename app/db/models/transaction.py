from sqlalchemy import String, Integer, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TransactionRaw(Base):
    __tablename__ = "transactions_raw"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    mono_transaction_id: Mapped[str] = mapped_column(String, unique=True)

    time: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[int] = mapped_column(Integer)

    description: Mapped[str] = mapped_column(String)
    mcc: Mapped[int] = mapped_column(Integer)

    raw_json: Mapped[dict] = mapped_column(JSON)