from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MerchantPlace(Base):
    __tablename__ = "merchant_places"

    id: Mapped[int] = mapped_column(primary_key=True)

    merchant_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("merchant_key", "place_id", name="uq_merchant_places_merchant_place"),
    )
