from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import get_admin_token


async def _create_cliente(client: AsyncClient, token: str, suffix: str) -> int:
    resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2C",
            "estado": "activo",
            "cliente_b2c": {
                "nombre_completo": f"Cliente Proyecto {suffix}",
                "documento_identidad": suffix,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id_cliente"]


@pytest.mark.asyncio
async def test_list_proyectos_empty(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy1")
    resp = await client.get(
        "/api/v1/proyectos/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_proyecto(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy2")
    id_cliente = await _create_cliente(client, token, "70000001")
    resp = await client.post(
        "/api/v1/proyectos/",
        json={
            "id_cliente": id_cliente,
            "nombre": "Sistema de Ciberseguridad",
            "descripcion": "Implementación SIEM",
            "estado": "propuesta",
            "presupuesto": 15000.00,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Sistema de Ciberseguridad"
    assert data["estado"] == "propuesta"


@pytest.mark.asyncio
async def test_get_proyecto(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy3")
    id_cliente = await _create_cliente(client, token, "70000002")
    create_resp = await client.post(
        "/api/v1/proyectos/",
        json={"id_cliente": id_cliente, "nombre": "Proyecto Alpha"},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_proyecto = create_resp.json()["id_proyecto"]
    resp = await client.get(
        f"/api/v1/proyectos/{id_proyecto}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id_proyecto"] == id_proyecto


@pytest.mark.asyncio
async def test_get_proyecto_not_found(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy4")
    resp = await client.get(
        "/api/v1/proyectos/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_proyecto_estado(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy5")
    id_cliente = await _create_cliente(client, token, "70000003")
    create_resp = await client.post(
        "/api/v1/proyectos/",
        json={"id_cliente": id_cliente, "nombre": "Proyecto Beta", "estado": "propuesta"},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_proyecto = create_resp.json()["id_proyecto"]
    resp = await client.patch(
        f"/api/v1/proyectos/{id_proyecto}",
        json={"estado": "en_progreso"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "en_progreso"


@pytest.mark.asyncio
async def test_create_tarea(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy6")
    id_cliente = await _create_cliente(client, token, "70000004")
    proyecto_resp = await client.post(
        "/api/v1/proyectos/",
        json={"id_cliente": id_cliente, "nombre": "Proyecto Gamma"},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_proyecto = proyecto_resp.json()["id_proyecto"]
    resp = await client.post(
        f"/api/v1/proyectos/{id_proyecto}/tareas",
        json={
            "id_proyecto": id_proyecto,
            "titulo": "Configurar firewall",
            "horas_estimadas": 8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["titulo"] == "Configurar firewall"


@pytest.mark.asyncio
async def test_delete_proyecto(client: AsyncClient) -> None:
    token = await get_admin_token(client, "proy7")
    id_cliente = await _create_cliente(client, token, "70000005")
    create_resp = await client.post(
        "/api/v1/proyectos/",
        json={"id_cliente": id_cliente, "nombre": "Proyecto Delta"},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_proyecto = create_resp.json()["id_proyecto"]
    del_resp = await client.delete(
        f"/api/v1/proyectos/{id_proyecto}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204
    get_resp = await client.get(
        f"/api/v1/proyectos/{id_proyecto}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404
