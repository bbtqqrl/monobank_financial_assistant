from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MONO_WEBHOOK_URL
from app.db.models.mono_accounts import MonoAccount
from app.db.models.mono_jars import MonoJar
from app.db.models.user import User
from app.services.api_client import MonobankAPIClient
from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository


class MonobankNotConnectedError(Exception):
    """The user has no Monobank token stored."""


class MonobankSyncService:

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

            # Accounts must be committed before the webhook goes live: Monobank
            # can start sending transactions right away, and one arriving for
            # an account we haven't saved yet would be dropped as unknown.
            await self.db.commit()

            await self.api.register_webhook(token, MONO_WEBHOOK_URL)
            
            return {
                "status": "ok",
                "clientId": client_info["clientId"],
            }
            
        finally:
            await self.api.close()

    async def refresh(self, user: User) -> tuple[list[MonoAccount], list[MonoJar]]:
        """Re-pull client-info with the user's stored token and bring their
        accounts and jars up to date (balances, new or closed cards/jars)."""
        if not user.mono_token:
            raise MonobankNotConnectedError()

        try:
            client_info = await self.api.get_client_info(user.mono_token)
        finally:
            await self.api.close()

        await self._sync_accounts(user, client_info.get("accounts", []))
        await self._sync_jars(user, client_info.get("jars", []))
        await self.db.commit()

        return await self.accounts.list_for_user(user.id), await self.jars.list_for_user(user.id)
    
    async def _deactivate_previous_accounts(self, user: User) -> None:
        for account in await self.accounts.list_for_user(user.id):
            account.is_active = False
        for jar in await self.jars.list_for_user(user.id):
            jar.is_active = False

    async def _sync_accounts(self, user: User, accounts: list[dict]) -> None:
        seen = set()
        for acc in accounts:
            seen.add(acc["id"])
            db_account = await self.accounts.get_by_mono_id(acc["id"])
            
            if db_account:
                await self.accounts.update(db_account, acc)
            else:
                await self.accounts.create(user, acc)

        # A card closed in Monobank just disappears from client-info.
        for db_account in await self.accounts.list_for_user(user.id):
            if db_account.mono_account_id not in seen:
                db_account.is_active = False
    
    async def _sync_jars(self, user: User, jars: list[dict]) -> None:
        seen = set()
        for jar in jars:
            seen.add(jar["id"])
            db_jar = await self.jars.get_by_mono_id(jar["id"])
            
            if db_jar:
                await self.jars.update(db_jar, jar)
            else:
                await self.jars.create(user, jar)

        for db_jar in await self.jars.list_for_user(user.id):
            if db_jar.mono_jar_id not in seen:
                db_jar.is_active = False
