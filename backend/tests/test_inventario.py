from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import get_admin_token


@pytest.mark.asyncio
async def test_delete_producto_removes_linked_quote_details(client: AsyncClient) -> None:
    token = await get_admin_token(client, "inv1")
    headers = {"Authorization": f"Bearer {token}"}

    cliente_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": "Cliente Inventario",
                "documento_identidad": "INV-001",
                "email": "inventario@example.com",
            },
        },
        headers=headers,
    )
    assert cliente_resp.status_code == 201
    id_cliente = cliente_resp.json()["id_cliente"]

    producto_resp = await client.post(
        "/api/v1/inventario/",
        json={
            "codigo": "INV-DELETE-001",
            "nombre": "Producto a eliminar",
            "categoria": "hardware",
            "requiere_serie": False,
            "stock_actual": 3,
            "stock_minimo": 1,
            "precio_venta": 150.0,
            "costo_adquisicion": 100.0,
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
                    "cantidad": 1,
                    "precio_unitario": 150.0,
                    "descuento": 0,
                }
            ],
        },
        headers=headers,
    )
    assert cotizacion_resp.status_code == 201
    id_cotizacion = cotizacion_resp.json()["id_cotizacion"]
    assert len(cotizacion_resp.json()["detalles"]) == 1

    delete_resp = await client.delete(
        f"/api/v1/inventario/{id_producto}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    producto_get_resp = await client.get(
        f"/api/v1/inventario/{id_producto}",
        headers=headers,
    )
    assert producto_get_resp.status_code == 404

    cotizacion_get_resp = await client.get(
        f"/api/v1/ventas/cotizaciones/{id_cotizacion}",
        headers=headers,
    )
    assert cotizacion_get_resp.status_code == 200
    assert cotizacion_get_resp.json()["detalles"] == []
