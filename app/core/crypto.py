import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import String, TypeDecorator

from app.core.config import MONO_TOKEN_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

_fernet = Fernet(MONO_TOKEN_ENCRYPTION_KEY)


def encrypt_value(value: str) -> str:
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")


class EncryptedString(TypeDecorator):
    """Transparently encrypts a string column at rest with Fernet."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return decrypt_value(value)
        except InvalidToken:
            logger.error(
                "Failed to decrypt an EncryptedString value (wrong/rotated key or corrupted data); "
                "treating column value as unset."
            )
            return None
