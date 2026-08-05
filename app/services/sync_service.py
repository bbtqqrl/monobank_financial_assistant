from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from services.api_client import MonobankAPIClient
from repositories.user import UserRepository
from repositories.account import AccountRepository
from repositories.jar import JarRepository

class MonobankSyncService:
    
    WEBHOOK_URL = "https://YOUR_NGROK_URL/webhooks/monobank"
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.users = UserRepository(db)
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
    
    async def connect(self, token: str) -> dict:
        try:
            client_info = await self.api.get_client_info(token)
            
            user = await self.users.create_or_update(
                client_id=client_info["clientId"],
                token=token
            )
            
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
