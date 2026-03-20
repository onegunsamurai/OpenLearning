from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.main import lifespan


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_scheme",
    [
        "sqlite+aiosqlite:///:memory:",
        "postgresql://localhost/db",
        "mysql+pymysql://localhost/db",
    ],
)
async def test_lifespan_rejects_invalid_database_url_scheme(bad_scheme: str) -> None:
    mock_settings = type("S", (), {"database_url": bad_scheme})()
    mock_app = AsyncMock()
    with (
        patch("app.main.settings", mock_settings),
        patch("app.main.init_db", new_callable=AsyncMock),
        pytest.raises(RuntimeError, match=r"postgresql\+asyncpg"),
    ):
        async with lifespan(mock_app):
            pass
