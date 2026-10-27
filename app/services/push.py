import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EXPO_ACCESS_TOKEN
from app.repositories.device import DeviceRepository

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
UNREGISTERED_ERROR = "DeviceNotRegistered"


class ExpoPushClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def send_silent(self, push_tokens: list[str], data: dict) -> list[str]:
        headers = {"Authorization": f"Bearer {EXPO_ACCESS_TOKEN}"} if EXPO_ACCESS_TOKEN else {}
        messages = [
            {"to": token, "data": data, "priority": "high", "_contentAvailable": True}
            for token in push_tokens
        ]
        try:
            async with httpx.AsyncClient(timeout=10, transport=self._transport) as client:
                response = await client.post(EXPO_PUSH_URL, json=messages, headers=headers)
                response.raise_for_status()
                tickets = response.json().get("data", [])
        except httpx.HTTPError:
            logger.warning("Expo push failed", exc_info=True)
            return []
        unregistered = []
        for token, ticket in zip(push_tokens, tickets):
            if ticket.get("status") == "error":
                error = (ticket.get("details") or {}).get("error")
                logger.warning("Expo push rejected: %s %s", error, ticket.get("message"))
                if error == UNREGISTERED_ERROR:
                    unregistered.append(token)
        return unregistered


class PushService:
    def __init__(self, db: AsyncSession, client: ExpoPushClient | None = None):
        self.db = db
        self.devices = DeviceRepository(db)
        self.client = client or ExpoPushClient()

    async def send_silent(self, user_id: int, data: dict) -> bool:
        tokens = await self.devices.list_tokens(user_id)
        if not tokens:
            return False
        unregistered = await self.client.send_silent(tokens, data)
        if unregistered:
            await self.devices.delete_tokens(unregistered)
            await self.db.commit()
        return len(unregistered) < len(tokens)
