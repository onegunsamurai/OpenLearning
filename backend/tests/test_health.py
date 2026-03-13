"""Tests for the health check endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_ok():
    """Health endpoint returns 200 when database is reachable."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_degraded():
    """Health endpoint returns 503 when database is unreachable."""
    mock_engine = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=Exception("connection refused"))
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_engine.connect = lambda: mock_conn

    with patch("app.routes.health._get_engine", return_value=mock_engine):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "unreachable"
