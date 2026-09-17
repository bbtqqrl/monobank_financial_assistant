from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def register(self, email: str, password: str) -> User:
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError(email)

        user = await self.users.create(email=email, password_hash=hash_password(password))
        await self.db.commit()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    async def issue_tokens(self, user: User) -> tuple[str, str]:
        access_token = create_access_token(user.id)

        raw_refresh_token = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=expires_at,
        )
        await self.db.commit()

        return access_token, raw_refresh_token

    async def refresh(self, raw_refresh_token: str) -> tuple[str, str]:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_valid_by_hash(token_hash)
        if stored is None:
            raise InvalidRefreshTokenError()

        user = await self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        await self.refresh_tokens.revoke(stored)
        return await self.issue_tokens(user)

    async def revoke(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_valid_by_hash(token_hash)
        if stored is not None:
            await self.refresh_tokens.revoke(stored)
            await self.db.commit()

    async def revoke_all(self, user_id: int) -> None:
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.db.commit()
