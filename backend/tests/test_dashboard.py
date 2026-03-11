from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import get_admin_token


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient) -> None:
    token = await get_admin_token(client, "dash1")
    resp = await client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clientes" in data
    assert "cotizaciones_mes" in data
    assert "tickets_abiertos" in data
    assert "productos_bajo_stock" in data
    # All values are non-negative integers
    for key in data:
        assert isinstance(data[key], int)
        assert data[key] >= 0


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_stats_reflect_clients(client: AsyncClient) -> None:
    """Stats total_clientes should increase as active clients are created."""
    token = await get_admin_token(client, "dash2")

    before = (
        await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()["total_clientes"]

    # Create an active B2C client
    await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "Stats Test User",
                "documento_identidad": "55667788",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    after = (
        await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()["total_clientes"]

    assert after == before + 1
