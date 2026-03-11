from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import get_admin_token


@pytest.mark.asyncio
async def test_list_clientes_empty(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli1")
    resp = await client.get(
        "/api/v1/clientes/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_cliente_b2b(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli2")
    resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Prueba SAC",
                "ruc": "20123456789",
                "contacto_principal": "Juan Pérez",
                "telefono": "999000111",
                "email": "empresa@prueba.pe",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo_cliente"] == "B2B"
    assert data["empresa"]["razon_social"] == "Empresa Prueba SAC"


@pytest.mark.asyncio
async def test_create_cliente_b2c(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli3")
    resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "María García",
                "documento_identidad": "12345678",
                "telefono": "987654321",
                "email": "maria@gmail.com",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo_cliente"] == "B2C"
    assert data["cliente_b2c"]["nombre_completo"] == "María García"


@pytest.mark.asyncio
async def test_create_cliente_b2b_missing_empresa(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli4")
    resp = await client.post(
        "/api/v1/clientes/",
        json={"tipo_cliente": "B2B", "estado": "activo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_cliente(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli5")
    create_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "Pedro Ramirez",
                "documento_identidad": "87654321",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    id_cliente = create_resp.json()["id_cliente"]
    resp = await client.get(
        f"/api/v1/clientes/{id_cliente}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id_cliente"] == id_cliente


@pytest.mark.asyncio
async def test_get_cliente_not_found(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli6")
    resp = await client.get(
        "/api/v1/clientes/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cliente_timeline(client: AsyncClient) -> None:
    token = await get_admin_token(client, "cli7")
    create_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "Ana Torres",
                "documento_identidad": "11223344",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    id_cliente = create_resp.json()["id_cliente"]
    resp = await client.get(
        f"/api/v1/clientes/{id_cliente}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    events = resp.json()
    # Creating a client auto-adds an ALTA event
    assert any(e["tipo_evento"] == "ALTA" for e in events)
