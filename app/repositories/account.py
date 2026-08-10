from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.models.user import User
from app.db.models.mono_accounts import MonoAccount


class AccountRepository:
   
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_mono_id(self, mono_account_id: str) -> Optional[MonoAccount]:
        result = await self.db.execute(
            select(MonoAccount).where(
                MonoAccount.mono_account_id == mono_account_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create(self, user: User, acc: dict) -> None:
        self.db.add(
            MonoAccount(
                user_id=user.id,
                mono_account_id=acc["id"],
                send_id=acc.get("sendId"),
                currency_code=acc["currencyCode"],
                cashback_type=acc.get("cashbackType"),
                balance=acc.get("balance", 0),
                credit_limit=acc.get("creditLimit", 0),
                masked_pan=self._extract_pan(acc),
                account_type=acc.get("type"),
                iban=acc.get("iban"),
            )
        )
    
    async def update(self, account: MonoAccount, acc: dict) -> None:
        account.send_id = acc.get("sendId")
        account.currency_code = acc["currencyCode"]
        account.cashback_type = acc.get("cashbackType")
        account.balance = acc.get("balance", 0)
        account.credit_limit = acc.get("creditLimit", 0)
        account.masked_pan = self._extract_pan(acc)
        account.account_type = acc.get("type")
        account.iban = acc.get("iban")
        account.is_active = True
    
    @staticmethod
    def _extract_pan(acc: dict) -> Optional[str]:
        pan = acc.get("maskedPan")
        return pan[0] if pan else None
