import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.services.api_client import MonobankAPIClient
from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository

class MonobankSyncService:

    WEBHOOK_URL = os.getenv("MONO_WEBHOOK_URL")

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
    
    async def connect(self, user: User, token: str) -> dict:
        try:
            client_info = await self.api.get_client_info(token)

            if user.mono_client_id and user.mono_client_id != client_info["clientId"]:
                await self._deactivate_previous_accounts(user)

            user.mono_client_id = client_info["clientId"]
            user.mono_token = token

            await self._sync_accounts(user, client_info.get("accounts", []))
            
            await self._sync_jars(user, client_info.get("jars", []))
            
            await self.api.register_webhook(token, self.WEBHOOK_URL)
            
            await self.db.commit()
            
            return {
                "status": "ok",
                "clientId": client_info["clientId"],
            }
            
        finally:
            await self.api.close()
    
    async def _deactivate_previous_accounts(self, user: User) -> None:
        for account in await self.accounts.list_for_user(user.id):
            account.is_active = False
        for jar in await self.jars.list_for_user(user.id):
            jar.is_active = False

    async def _sync_accounts(self, user: User, accounts: list[dict]) -> None:
        for acc in accounts:
            db_account = await self.accounts.get_by_mono_id(acc["id"])
            
            if db_account:
                await self.accounts.update(db_account, acc)
            else:
                await self.accounts.create(user, acc)
    
    async def _sync_jars(self, user: User, jars: list[dict]) -> None:
        for jar in jars:
            db_jar = await self.jars.get_by_mono_id(jar["id"])
            
            if db_jar:
                await self.jars.update(db_jar, jar)
            else:
                await self.jars.create(user, jar)
