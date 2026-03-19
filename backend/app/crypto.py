from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _get_fernet() -> Fernet:
    """Return a Fernet instance, raising ValueError if key is not configured."""
    key = get_settings().encryption_key
    if not key:
        raise ValueError("ENCRYPTION_KEY is not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key and return the ciphertext as a UTF-8 string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to plaintext. Raises ValueError on failure."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt API key — invalid or corrupted ciphertext") from e
