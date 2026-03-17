from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import get_admin_token


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
