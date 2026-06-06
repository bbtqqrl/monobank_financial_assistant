import httpx


class MonobankService:
    BASE_URL = "https://api.monobank.ua"

    async def get_client_info(self, token: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/personal/client-info",
                headers={"X-Token": token},
            )

            response.raise_for_status()

            return response.json()

    async def register_webhook(self, token: str, webhook_url: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/personal/webhook",
                headers={"X-Token": token},
                json={"webHookUrl": webhook_url},
            )

            response.raise_for_status()

            return response.json()