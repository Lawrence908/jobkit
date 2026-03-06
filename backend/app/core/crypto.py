"""Fernet encryption for Google refresh tokens."""
import base64
import secrets
from cryptography.fernet import Fernet, InvalidToken


def make_fernet_key_from_secret(secret: str) -> bytes:
    """Derive a valid Fernet key (32 url-safe base64 bytes) from a secret string."""
    if len(secret) >= 32:
        raw = secret.encode("utf-8")[:32].ljust(32, b"\x00")
    else:
        raw = (secret.encode("utf-8") * 4)[:32]
    return base64.urlsafe_b64encode(raw)


def encrypt_refresh_token(plaintext: str, encryption_key: str) -> str:
    """Encrypt a refresh token for storage."""
    key = make_fernet_key_from_secret(encryption_key)
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(ciphertext: str, encryption_key: str) -> str | None:
    """Decrypt a stored refresh token. Returns None if invalid."""
    try:
        key = make_fernet_key_from_secret(encryption_key)
        f = Fernet(key)
        return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, Exception):
        return None


def generate_encryption_key() -> str:
    """Generate a 32-byte secret suitable for GOOGLE_TOKEN_ENCRYPTION_KEY."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
