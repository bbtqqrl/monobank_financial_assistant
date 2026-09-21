import base64
import logging

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

logger = logging.getLogger(__name__)

SERVER_KEY_URL = "https://api.monobank.ua/bank/sync"


class MonobankSignatureVerifier:
    """Verifies the X-Sign header Monobank attaches to webhook requests.

    Monobank signs the raw request body with ECDSA (secp256k1, SHA-256) and
    publishes its current public key at /bank/sync as a base64-encoded raw
    uncompressed EC point (65 bytes, 0x04 prefix) alongside a key id. The
    signature itself has historically arrived in either DER or raw r||s
    (64-byte) form, so both are tried.
    """

    def __init__(self):
        self._public_key: ec.EllipticCurvePublicKey | None = None
        self._key_id: str | None = None

    async def verify(self, body: bytes, x_sign_b64: str, x_key_id: str | None) -> bool:
        if not x_sign_b64:
            return False

        try:
            signature = base64.b64decode(x_sign_b64)
        except (ValueError, TypeError):
            return False

        if self._public_key is None or (x_key_id and x_key_id != self._key_id):
            await self._refresh_key()

        if self._public_key is None:
            return False

        return self._verify_with_key(self._public_key, body, signature)

    async def _refresh_key(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(SERVER_KEY_URL)
                response.raise_for_status()
                data = response.json()

            raw_point = base64.b64decode(data["serverPubKey"])
            self._public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), raw_point)
            self._key_id = data.get("serverKeyId")
        except Exception:
            logger.exception("Failed to fetch Monobank server public key")
            self._public_key = None
            self._key_id = None

    @staticmethod
    def _verify_with_key(public_key: ec.EllipticCurvePublicKey, body: bytes, signature: bytes) -> bool:
        try:
            public_key.verify(signature, body, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except ValueError:
            pass

        if len(signature) != 64:
            return False

        try:
            r = int.from_bytes(signature[:32], "big")
            s = int.from_bytes(signature[32:], "big")
            der_signature = encode_dss_signature(r, s)
            public_key.verify(der_signature, body, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False


monobank_signature_verifier = MonobankSignatureVerifier()
