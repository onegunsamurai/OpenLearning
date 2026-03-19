from __future__ import annotations

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.crypto import decrypt_api_key, encrypt_api_key

# Generate a stable test key for all tests in this module
_TEST_KEY = Fernet.generate_key().decode()


def _mock_settings():
    """Return a mock settings object with a test encryption key."""
    from app.config import Settings

    return Settings(encryption_key=_TEST_KEY)


@patch("app.crypto.get_settings", _mock_settings)
class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        plaintext = "sk-ant-api03-very-secret-key-12345"
        ciphertext = encrypt_api_key(plaintext)
        assert ciphertext != plaintext
        assert decrypt_api_key(ciphertext) == plaintext

    def test_decrypt_invalid_ciphertext_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_api_key("not-valid-ciphertext")

    def test_encrypt_empty_string(self) -> None:
        ciphertext = encrypt_api_key("")
        assert decrypt_api_key(ciphertext) == ""

    def test_different_calls_produce_different_ciphertext(self) -> None:
        plaintext = "sk-test-key"
        ct1 = encrypt_api_key(plaintext)
        ct2 = encrypt_api_key(plaintext)
        # Fernet uses a random IV so ciphertexts should differ
        assert ct1 != ct2
        # But both decrypt to the same value
        assert decrypt_api_key(ct1) == plaintext
        assert decrypt_api_key(ct2) == plaintext


class TestCryptoMissingKey:
    def test_encrypt_raises_when_key_not_configured(self) -> None:
        with patch("app.crypto.get_settings") as mock:
            mock.return_value.encryption_key = ""
            with pytest.raises(ValueError, match="ENCRYPTION_KEY is not configured"):
                encrypt_api_key("test")
