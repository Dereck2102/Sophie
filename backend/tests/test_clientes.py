from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import get_admin_token


async def _create_tenant_admin(
    client: AsyncClient,
    *,
    super_headers: dict[str, str],
    tenant_id: int,
    username: str,
    email: str,
    password: str,
) -> dict[str, str]:
    create_resp = await client.post(
        "/api/v1/usuarios/",
        json={
            "id_cliente": tenant_id,
            "username": username,
            "email": email,
            "password": password,
            "rol": "admin",
        },
        headers=super_headers,
    )
    assert create_resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


async def _get_owner_super_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "damacoria",
            "email": "damacoria@bigsolutions.pe",
            "password": "OwnerPass123!",
            "rol": "superadmin",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "damacoria", "password": "OwnerPass123!"},
    )
    assert login_resp.status_code == 200
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


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


@pytest.mark.asyncio
async def test_legacy_cliente_tenant_fallback_allows_same_tenant_access(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    super_headers = await _get_owner_super_headers(client)

    empresa_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Legacy Cliente OK",
                "ruc": "20999910101",
                "contacto_principal": "Legacy Admin",
                "telefono": "0999010101",
                "email": "legacy_cliente_ok@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_resp.status_code == 201
    tenant_id = empresa_resp.json()["id_cliente"]

    tenant_headers = await _create_tenant_admin(
        client,
        super_headers=super_headers,
        tenant_id=tenant_id,
        username="tenant_legacy_cli_ok",
        email="tenant_legacy_cli_ok@bigsolutions.pe",
        password="TenantLegacy123!",
    )

    await db_session.execute(
        text("UPDATE cliente SET tenant_id = NULL WHERE id_cliente = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    await db_session.flush()

    list_resp = await client.get("/api/v1/clientes/", headers=tenant_headers)
    assert list_resp.status_code == 200
    ids = {item["id_cliente"] for item in list_resp.json()}
    assert tenant_id in ids

    get_resp = await client.get(f"/api/v1/clientes/{tenant_id}", headers=tenant_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id_cliente"] == tenant_id


@pytest.mark.asyncio
async def test_legacy_cliente_tenant_fallback_blocks_cross_tenant_access(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    super_headers = await _get_owner_super_headers(client)

    empresa_a_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Legacy A",
                "ruc": "20999910201",
                "contacto_principal": "Tenant A",
                "telefono": "0999010201",
                "email": "legacy_a@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_a_resp.status_code == 201
    tenant_a_id = empresa_a_resp.json()["id_cliente"]

    tenant_a_headers = await _create_tenant_admin(
        client,
        super_headers=super_headers,
        tenant_id=tenant_a_id,
        username="tenant_legacy_cli_a",
        email="tenant_legacy_cli_a@bigsolutions.pe",
        password="TenantLegacy123!",
    )

    empresa_b_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Legacy B",
                "ruc": "20999910202",
                "contacto_principal": "Tenant B",
                "telefono": "0999010202",
                "email": "legacy_b@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_b_resp.status_code == 201
    tenant_b_id = empresa_b_resp.json()["id_cliente"]

    await db_session.execute(
        text("UPDATE cliente SET tenant_id = NULL WHERE id_cliente IN (:tenant_a_id, :tenant_b_id)"),
        {"tenant_a_id": tenant_a_id, "tenant_b_id": tenant_b_id},
    )
    await db_session.flush()

    forbidden_resp = await client.get(f"/api/v1/clientes/{tenant_b_id}", headers=tenant_a_headers)
    assert forbidden_resp.status_code == 403
