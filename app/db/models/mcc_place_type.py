from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MccPlaceType(Base):
    __tablename__ = "mcc_place_types"

    mcc: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    google_types: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)
    apple_categories: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)

    @property
    def searchable(self) -> bool:
        return bool(self.google_types or self.apple_categories)
