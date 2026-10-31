from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.repositories.mcc_place_type import MccPlaceTypeRepository
from app.repositories.place import PlaceRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_place import UserPlaceRepository
from app.schemas.place import PlaceResponse
from app.services.errors import InvalidRequestError, NotFoundError, ServiceUnavailableError
from app.services.merchant_key import build_merchant_key
from app.services.place_matching import CONFIDENT_PLACE_METHODS, PlaceMethod, choose_place
from app.services.places import PlaceService, distance_m

LINK_RADIUS_M = 150
CANDIDATES_RADIUS_M = 50


class TransactionLocationService:

    def __init__(self, db: AsyncSession, user_id: int, places: PlaceService | None = None):
        self.db = db
        self.user_id = user_id
        self.places = places or PlaceService()
        self.place_repo = PlaceRepository(db)
        self.user_places = UserPlaceRepository(db)
        self.mcc_types = MccPlaceTypeRepository(db)
        self.transactions = TransactionRepository(db)

    async def set_location(self, transaction_id: int, latitude: float, longitude: float) -> TransactionRaw:
        transaction = await self._get(transaction_id)
        if transaction.latitude is not None:
            return transaction
        place, method = await self._locate(transaction, latitude, longitude)
        transaction.latitude = latitude
        transaction.longitude = longitude
        transaction.place = place
        transaction.place_method = method
        await self.db.commit()
        return transaction

    async def retry_place(self, transaction_id: int) -> bool:
        transaction = await self._get(transaction_id)
        if transaction.latitude is None or transaction.place_method is not None or transaction.place is not None:
            return False
        place, method = await self._locate(transaction, transaction.latitude, transaction.longitude)
        if method is None:
            return False
        if not await self.transactions.set_found_place(transaction.id, place.id if place else None, method):
            await self.db.rollback()
            return False
        await self.db.commit()
        return True

    async def place_candidates(self, transaction_id: int) -> list[PlaceResponse]:
        return await self._search_around(await self._get(transaction_id))

    async def give_feedback(self, transaction_id: int, correct: bool, place_id: str | None = None) -> TransactionRaw:
        transaction = await self._get(transaction_id)
        merchant_key = build_merchant_key(transaction.description or "")
        if correct:
            if transaction.place is None:
                raise InvalidRequestError("Transaction has no place to confirm")
            if place_id is not None:
                raise InvalidRequestError("place_id can only be sent with correct=false")
            if merchant_key:
                await self.user_places.save(self.user_id, merchant_key, transaction.place.id, rejected=False)
            transaction.place_confirmed = True
        else:
            wrong = transaction.place
            if wrong is not None and merchant_key:
                await self.user_places.save(self.user_id, merchant_key, wrong.id, rejected=True)
            if place_id:
                chosen = await self._pick_candidate(transaction, place_id)
                if wrong is not None and wrong.id != chosen.id:
                    transaction.rejected_place_id = wrong.id
                transaction.place = chosen
                transaction.place_confirmed = True
                if merchant_key:
                    await self.user_places.save(self.user_id, merchant_key, chosen.id, rejected=False)
            else:
                transaction.place_confirmed = False
        await self.db.commit()
        return transaction

    async def _get(self, transaction_id: int) -> TransactionRaw:
        transaction = await self.transactions.get_by_id_for_user(transaction_id, self.user_id)
        if transaction is None:
            raise NotFoundError("Transaction not found")
        return transaction

    async def _search_around(self, transaction: TransactionRaw) -> list[PlaceResponse]:
        if transaction.latitude is None or transaction.longitude is None:
            raise InvalidRequestError("Transaction has no location")
        place_filter = await self.mcc_types.get(transaction.mcc) if transaction.mcc is not None else None
        if place_filter is None or not place_filter.searchable:
            return []
        return await self.places.search(transaction.latitude, transaction.longitude, place_filter, CANDIDATES_RADIUS_M)

    async def _pick_candidate(self, transaction: TransactionRaw, place_id: str) -> Place:
        candidates = await self._search_around(transaction)
        found = next((candidate for candidate in candidates if candidate.place_id == place_id), None)
        if found is None:
            raise InvalidRequestError("Place is not among the candidates")
        return await self.place_repo.upsert(found)

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
            return None, None

        if merchant_key:
            rejected = await self.user_places.rejected_provider_ids(self.user_id, merchant_key)
            candidates = [candidate for candidate in candidates if candidate.place_id not in rejected]
        found, method = choose_place(candidates, transaction.description or "")
        if found is None:
            return None, method

        place = await self.place_repo.upsert(found)
        if merchant_key and method in CONFIDENT_PLACE_METHODS:
            await self.user_places.save(self.user_id, merchant_key, place.id, rejected=False)
        return place, method

    async def _linked_place(self, merchant_key: str, latitude: float, longitude: float) -> Place | None:
        if not merchant_key:
            return None
        places = await self.user_places.list_near(self.user_id, merchant_key, latitude, longitude, LINK_RADIUS_M)
        distance = {place.id: distance_m(latitude, longitude, place.latitude, place.longitude) for place in places}
        nearby = [place for place in places if distance[place.id] <= LINK_RADIUS_M]
        return min(nearby, key=lambda place: distance[place.id], default=None)
