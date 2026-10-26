from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.repositories.place import PlaceRepository
from app.repositories.transaction import TransactionRepository
from app.services.errors import NotFoundError, ServiceUnavailableError
from app.services.places import PlaceService, distance_m

KNOWN_PLACE_RADIUS_M = 50


class TransactionLocationService:

    def __init__(self, db: AsyncSession, user_id: int, places: PlaceService | None = None):
        self.db = db
        self.user_id = user_id
        self.places = places or PlaceService()
        self.place_repo = PlaceRepository(db)
        self.transactions = TransactionRepository(db)

    async def set_location(self, transaction_id: int, latitude: float, longitude: float) -> TransactionRaw:
        transaction = await self.transactions.get_by_id_for_user(transaction_id, self.user_id)
        if transaction is None:
            raise NotFoundError("Transaction not found")

        place = await self._known_place(transaction, latitude, longitude) or await self._find_place(latitude, longitude)
        transaction.latitude = latitude
        transaction.longitude = longitude
        transaction.place = place
        await self.db.commit()
        return transaction

    async def _known_place(self, transaction: TransactionRaw, latitude: float, longitude: float) -> Place | None:
        if transaction.merchant_mapping_id is None:
            return None
        places = await self.place_repo.list_for_merchant(self.user_id, transaction.merchant_mapping_id)
        distance = {place.id: distance_m(latitude, longitude, place.latitude, place.longitude) for place in places}
        nearby = [place for place in places if distance[place.id] <= KNOWN_PLACE_RADIUS_M]
        return min(nearby, key=lambda place: distance[place.id], default=None)

    async def _find_place(self, latitude: float, longitude: float) -> Place | None:
        try:
            found = await self.places.nearest(latitude, longitude)
        except ServiceUnavailableError:
            # TODO: повторити пошук місця пізніше для транзакцій з координатами, але без place_id
            return None
        return await self.place_repo.upsert(found) if found else None
