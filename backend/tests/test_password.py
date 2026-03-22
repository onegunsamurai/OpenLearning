from __future__ import annotations

from app.password import hash_password, verify_password


class TestHashPassword:
    def test_returns_bcrypt_string(self) -> None:
        hashed = hash_password("mysecretpassword")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self) -> None:
        hashed = hash_password("correct-password")
        assert verify_password("correct-password", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_malformed_hash_returns_false(self) -> None:
        assert verify_password("password", "not-a-valid-hash") is False

    def test_salt_uniqueness(self) -> None:
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2
        # Both still verify correctly
        assert verify_password("same-password", h1) is True
        assert verify_password("same-password", h2) is True
