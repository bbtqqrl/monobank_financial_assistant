import httpx
from typing import Optional


class MonobankAPIClient:
    BASE_URL = "https://api.monobank.ua"
    
    def __init__(self, timeout: int = 10):
        self._client: Optional[httpx.AsyncClient] = None
        self.timeout = timeout
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def get_client_info(self, token: str) -> dict:
        client = await self._get_client()
        r = await client.get(
            f"{self.BASE_URL}/personal/client-info",
            headers={"X-Token": token},
        )
        r.raise_for_status()
        return r.json()
    
    async def register_webhook(self, token: str, webhook_url: str) -> dict:
        client = await self._get_client()
        r = await client.post(
            f"{self.BASE_URL}/personal/webhook",
            headers={"X-Token": token},
            json={"webHookUrl": webhook_url},
        )
        r.raise_for_status()
        return r.json()
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
