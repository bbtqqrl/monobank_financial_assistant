from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.currencies import UAH
from app.db.models.transaction import TransactionRaw
from app.repositories.account import AccountRepository
from app.repositories.category import CategoryRepository
from app.repositories.jar import JarRepository
from app.repositories.transaction import TransactionRepository
from app.services.categorization_service import CategoryDirectionError, check_category_fits_amount
from app.services.errors import InvalidRequestError, NotFoundError


class TransactionService:

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.transactions = TransactionRepository(db)
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
        self.categories = CategoryRepository(db)

    async def create_manual(
        self,
        description: str,
        amount: int,
        category_id: int,
        account_id: int | None = None,
        jar_id: int | None = None,
        currency_code: int | None = None,
        time: int | None = None,
        comment: str | None = None,
    ) -> TransactionRaw:
        if account_id is not None and jar_id is not None:
            raise InvalidRequestError("A transaction can belong to an account or a jar, not both")

        holder_currency = None
        if account_id is not None:
            account = await self.accounts.get_by_id_for_user(account_id, self.user_id)
            if account is None:
                raise NotFoundError("Account not found")
            holder_currency = account.currency_code
        if jar_id is not None:
            jar = await self.jars.get_by_id_for_user(jar_id, self.user_id)
            if jar is None:
                raise NotFoundError("Jar not found")
            holder_currency = jar.currency_code

        if holder_currency is not None and currency_code not in (None, holder_currency):
            raise InvalidRequestError(f"currency_code must match the account's currency ({holder_currency})")

        category = await self.categories.get_selectable_by_id(category_id)
        if category is None:
            raise InvalidRequestError("Category not found or not selectable")
        try:
            check_category_fits_amount(category.kind, amount)
        except CategoryDirectionError as e:
            raise InvalidRequestError(str(e))

        transaction = await self.transactions.create_manual(
            user_id=self.user_id,
            account_id=account_id,
            jar_id=jar_id,
            description=description,
            amount=amount,
            currency_code=holder_currency or currency_code or UAH,
            time=time if time is not None else int(datetime.now(timezone.utc).timestamp()),
            comment=comment,
            category_id=category.id,
        )
        await self.db.commit()
        return transaction
