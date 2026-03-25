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
async def test_cotizacion_uses_deterministic_money_rounding(client: AsyncClient) -> None:
    token = await get_admin_token(client, "venprec1")
    headers = {"Authorization": f"Bearer {token}"}

    cliente_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "Cliente Precision",
                "documento_identidad": "PREC-001",
                "email": "precision@example.com",
            },
        },
        headers=headers,
    )
    assert cliente_resp.status_code == 201
    id_cliente = cliente_resp.json()["id_cliente"]

    producto_resp = await client.post(
        "/api/v1/inventario/",
        json={
            "codigo": "PREC-INV-001",
            "nombre": "Producto precisión",
            "categoria": "hardware",
            "requiere_serie": False,
            "stock_actual": 10,
            "stock_minimo": 1,
            "precio_venta": 0.1,
            "costo_adquisicion": 0.03,
        },
        headers=headers,
    )
    assert producto_resp.status_code == 201
    id_producto = producto_resp.json()["id_producto"]

    cotizacion_resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={
            "id_cliente": id_cliente,
            "detalles": [
                {
                    "id_producto": id_producto,
                    "cantidad": 3,
                    "precio_unitario": 0.1,
                    "descuento": 0,
                }
            ],
        },
        headers=headers,
    )
    assert cotizacion_resp.status_code == 201

    data = cotizacion_resp.json()
    assert data["subtotal"] == pytest.approx(0.30)
    assert data["impuesto"] == pytest.approx(0.05)
    assert data["total"] == pytest.approx(0.35)
    assert data["detalles"][0]["subtotal"] == pytest.approx(0.30)


@pytest.mark.asyncio
async def test_legacy_cotizacion_tenant_fallback_allows_same_tenant_delete(
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
                "razon_social": "Empresa Legacy Ventas OK",
                "ruc": "20999920101",
                "contacto_principal": "Ventas Tenant",
                "telefono": "0999020101",
                "email": "legacy_ventas_ok@bigsolutions.pe",
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
        username="tenant_legacy_ven_ok",
        email="tenant_legacy_ven_ok@bigsolutions.pe",
        password="TenantLegacy123!",
    )

    producto_resp = await client.post(
        "/api/v1/inventario/",
        json={
            "codigo": "LEG-VEN-OK-001",
            "nombre": "Producto Legacy Ventas OK",
            "categoria": "hardware",
            "requiere_serie": False,
            "stock_actual": 10,
            "stock_minimo": 1,
            "precio_venta": 10,
            "costo_adquisicion": 2,
        },
        headers=super_headers,
    )
    assert producto_resp.status_code == 201
    id_producto = producto_resp.json()["id_producto"]

    cotizacion_resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={
            "id_cliente": tenant_id,
            "detalles": [
                {
                    "id_producto": id_producto,
                    "cantidad": 1,
                    "precio_unitario": 10,
                    "descuento": 0,
                }
            ],
        },
        headers=super_headers,
    )
    assert cotizacion_resp.status_code == 201
    cotizacion_id = cotizacion_resp.json()["id_cotizacion"]

    await db_session.execute(
        text("UPDATE cotizacion SET tenant_id = NULL WHERE id_cotizacion = :id"),
        {"id": cotizacion_id},
    )
    await db_session.flush()

    delete_resp = await client.delete(
        f"/api/v1/ventas/cotizaciones/{cotizacion_id}",
        headers=tenant_headers,
    )
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_legacy_cotizacion_tenant_fallback_blocks_cross_tenant_delete(
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
                "razon_social": "Empresa Legacy Ventas A",
                "ruc": "20999920201",
                "contacto_principal": "Tenant A",
                "telefono": "0999020201",
                "email": "legacy_ventas_a@bigsolutions.pe",
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
        username="tenant_legacy_ven_a",
        email="tenant_legacy_ven_a@bigsolutions.pe",
        password="TenantLegacy123!",
    )

    empresa_b_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Legacy Ventas B",
                "ruc": "20999920202",
                "contacto_principal": "Tenant B",
                "telefono": "0999020202",
                "email": "legacy_ventas_b@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_b_resp.status_code == 201
    tenant_b_id = empresa_b_resp.json()["id_cliente"]

    producto_resp = await client.post(
        "/api/v1/inventario/",
        json={
            "codigo": "LEG-VEN-BLK-001",
            "nombre": "Producto Legacy Ventas Block",
            "categoria": "hardware",
            "requiere_serie": False,
            "stock_actual": 10,
            "stock_minimo": 1,
            "precio_venta": 12,
            "costo_adquisicion": 3,
        },
        headers=super_headers,
    )
    assert producto_resp.status_code == 201
    id_producto = producto_resp.json()["id_producto"]

    cotizacion_resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={
            "id_cliente": tenant_b_id,
            "detalles": [
                {
                    "id_producto": id_producto,
                    "cantidad": 1,
                    "precio_unitario": 12,
                    "descuento": 0,
                }
            ],
        },
        headers=super_headers,
    )
    assert cotizacion_resp.status_code == 201
    cotizacion_id = cotizacion_resp.json()["id_cotizacion"]

    await db_session.execute(
        text("UPDATE cotizacion SET tenant_id = NULL WHERE id_cotizacion = :id"),
        {"id": cotizacion_id},
    )
    await db_session.flush()

    forbidden_resp = await client.delete(
        f"/api/v1/ventas/cotizaciones/{cotizacion_id}",
        headers=tenant_a_headers,
    )
    assert forbidden_resp.status_code == 403
