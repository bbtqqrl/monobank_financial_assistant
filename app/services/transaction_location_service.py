from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.repositories.mcc_place_type import MccPlaceTypeRepository
from app.repositories.merchant_place import MerchantPlaceRepository
from app.repositories.place import PlaceRepository
from app.repositories.transaction import TransactionRepository
from app.services.errors import NotFoundError, ServiceUnavailableError
from app.services.merchant_key import build_merchant_key
from app.services.place_matching import CONFIDENT_PLACE_METHODS, PlaceMethod, choose_place
from app.services.places import PlaceService, distance_m

LINK_RADIUS_M = 150


class TransactionLocationService:

    def __init__(self, db: AsyncSession, user_id: int, places: PlaceService | None = None):
        self.db = db
        self.user_id = user_id
        self.places = places or PlaceService()
        self.place_repo = PlaceRepository(db)
        self.links = MerchantPlaceRepository(db)
        self.mcc_types = MccPlaceTypeRepository(db)
        self.transactions = TransactionRepository(db)

    async def set_location(self, transaction_id: int, latitude: float, longitude: float) -> TransactionRaw:
        transaction = await self.transactions.get_by_id_for_user(transaction_id, self.user_id)
        if transaction is None:
            raise NotFoundError("Transaction not found")

        place, method = await self._locate(transaction, latitude, longitude)
        transaction.latitude = latitude
        transaction.longitude = longitude
        transaction.place = place
        transaction.place_method = method
        await self.db.commit()
        return transaction

    async def _locate(
        self, transaction: TransactionRaw, latitude: float, longitude: float,
    ) -> tuple[Place | None, PlaceMethod | None]:
        place_filter = await self.mcc_types.get(transaction.mcc) if transaction.mcc is not None else None
        if place_filter is None or not place_filter.searchable:
            return None, PlaceMethod.SKIPPED

        merchant_key = build_merchant_key(transaction.description or "")
        linked = await self._linked_place(merchant_key, latitude, longitude)
        if linked is not None:
            return linked, PlaceMethod.LINK

        try:
            candidates = await self.places.search(latitude, longitude, place_filter)
        except ServiceUnavailableError:
            # TODO: повторити пошук місця пізніше для транзакцій з координатами, але без place_method
            return None, None

        found, method = choose_place(candidates, transaction.description or "")
        if found is None:
            return None, method

        place = await self.place_repo.upsert(found)
        if merchant_key and method in CONFIDENT_PLACE_METHODS:
            await self.links.link(merchant_key, place.id)
        return place, method

    async def _linked_place(self, merchant_key: str, latitude: float, longitude: float) -> Place | None:
        if not merchant_key:
            return None
        places = await self.links.list_near(merchant_key, latitude, longitude, LINK_RADIUS_M)
        distance = {place.id: distance_m(latitude, longitude, place.latitude, place.longitude) for place in places}
        nearby = [place for place in places if distance[place.id] <= LINK_RADIUS_M]
        return min(nearby, key=lambda place: distance[place.id], default=None)
