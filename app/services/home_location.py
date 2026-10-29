import math
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.repositories.place import PlaceRepository
from app.services.places import METERS_PER_DEGREE, distance_m

HOME_RADIUS_M = 50
MIN_HOME_POINTS = 5
HOME_LOOKBACK_DAYS = 180
MAX_HOME_POINTS = 2000
HOME_SHIFT_STEPS = 5


@dataclass(frozen=True)
class Home:
    latitude: float
    longitude: float
    source: Literal["auto", "user"]


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def infer_home(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if len(points) < MIN_HOME_POINTS:
        return None
    lat_step = HOME_RADIUS_M / METERS_PER_DEGREE
    lon_step = lat_step / math.cos(math.radians(points[0][0]))
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for point in points:
        grid[(math.floor(point[0] / lat_step), math.floor(point[1] / lon_step))].append(point)

    best: list[tuple[float, float]] = []
    for (row, column), cell in grid.items():
        around = [p for dr in (-2, -1, 0, 1, 2) for dc in (-2, -1, 0, 1, 2) for p in grid.get((row + dr, column + dc), [])]
        center = _centroid(cell)
        close: list[tuple[float, float]] = []
        for _ in range(HOME_SHIFT_STEPS):
            close = [p for p in around if distance_m(center[0], center[1], p[0], p[1]) <= HOME_RADIUS_M]
            center = _centroid(close)
        if len(close) > len(best):
            best = close
    return _centroid(best) if len(best) >= MIN_HOME_POINTS else None


class HomeService:

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.places = PlaceRepository(db)

    async def location(self) -> Home | None:
        if self.user.home_latitude is not None and self.user.home_longitude is not None:
            return Home(self.user.home_latitude, self.user.home_longitude, "user")
        since = int(time.time()) - HOME_LOOKBACK_DAYS * 24 * 3600
        found = infer_home(await self.places.unplaced_points(self.user.id, since, MAX_HOME_POINTS))
        return Home(found[0], found[1], "auto") if found else None

    async def set(self, latitude: float, longitude: float) -> Home:
        self.user.home_latitude = latitude
        self.user.home_longitude = longitude
        await self.db.commit()
        return Home(latitude, longitude, "user")

    async def reset(self) -> None:
        self.user.home_latitude = None
        self.user.home_longitude = None
        await self.db.commit()
