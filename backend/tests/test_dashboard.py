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

    int_fields = [
        "total_clientes",
        "cotizaciones_mes",
        "tickets_abiertos",
        "productos_bajo_stock",
        "revenue_mes",
        "proyectos_activos",
    ]
    float_fields = ["margen_bruto_mes", "caja_chica_balance", "caja_chica_egresos_mes"]

    for key in int_fields:
        assert isinstance(data[key], int)
        assert data[key] >= 0

    for key in float_fields:
        assert isinstance(data[key], (int, float))


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


@pytest.mark.asyncio
async def test_dashboard_analytics_shape(client: AsyncClient) -> None:
    token = await get_admin_token(client, "dash3")
    resp = await client.get(
        "/api/v1/dashboard/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "tendencia_mensual" in data
    assert isinstance(data["tendencia_mensual"], list)
    assert len(data["tendencia_mensual"]) == 6

    assert "correlaciones" in data
    assert isinstance(data["correlaciones"], list)
