from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.auditoria import LogAuditoria
from tests.helpers import get_admin_token


async def _get_owner_admin_token(client: AsyncClient) -> str:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "damacoria",
            "email": "damacoria@bigsolutions.pe",
            "password": "OwnerPass123!",
            "rol": "superadmin",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "damacoria", "password": "OwnerPass123!"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


async def _create_empresa(client: AsyncClient, token: str, suffix: str) -> int:
    response = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": f"Empresa Boveda {suffix}",
                "ruc": f"20{suffix.zfill(9)}",
                "contacto_principal": "Contacto Prueba",
                "telefono": "0999000111",
                "email": f"boveda_{suffix}@bigsolutions.pe",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id_cliente"]


async def _create_user_and_login(
    client: AsyncClient,
    admin_token: str,
    *,
    username: str,
    email: str,
    role: str,
    id_cliente: int | None = None,
) -> str:
    payload = {
        "username": username,
        "email": email,
        "password": "UserPass123!",
        "rol": role,
    }
    if id_cliente is not None:
        payload["id_cliente"] = id_cliente

    create_response = await client.post(
        "/api/v1/usuarios/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "UserPass123!"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_boveda_crud_and_audit_flow(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_token = await get_admin_token(client, "boveda1")
    id_empresa = await _create_empresa(client, admin_token, "123456789")

    create_response = await client.post(
        "/api/v1/boveda/",
        json={
            "id_empresa": id_empresa,
            "nombre": "ERP Cliente",
            "usuario_acceso": "admin.erp",
            "password_plain": "Secret#123",
            "url": "https://erp.cliente.pe",
            "notas": "Acceso principal",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    credencial = create_response.json()
    id_credencial = credencial["id_credencial"]

    reveal_response = await client.get(
        f"/api/v1/boveda/{id_credencial}/reveal",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reveal_response.status_code == 200
    assert reveal_response.json()["password_plain"] == "Secret#123"

    update_response = await client.patch(
        f"/api/v1/boveda/{id_credencial}",
        json={"nombre": "ERP Cliente Producción", "password_plain": "NewSecret#456"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["nombre"] == "ERP Cliente Producción"

    reveal_updated_response = await client.get(
        f"/api/v1/boveda/{id_credencial}/reveal",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reveal_updated_response.status_code == 200
    assert reveal_updated_response.json()["password_plain"] == "NewSecret#456"

    delete_response = await client.delete(
        f"/api/v1/boveda/{id_credencial}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204

    reveal_deleted_response = await client.get(
        f"/api/v1/boveda/{id_credencial}/reveal",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reveal_deleted_response.status_code == 404

    logs_result = await db_session.execute(
        select(LogAuditoria.accion).where(LogAuditoria.modulo == "boveda")
    )
    actions = list(logs_result.scalars().all())
    assert "VAULT_CREATE" in actions
    assert "VAULT_ACCESS" in actions
    assert "VAULT_UPDATE" in actions
    assert "VAULT_DELETE" in actions


@pytest.mark.asyncio
async def test_boveda_create_requires_existing_empresa(client: AsyncClient) -> None:
    admin_token = await get_admin_token(client, "boveda2")

    response = await client.post(
        "/api/v1/boveda/",
        json={
            "id_empresa": 999999,
            "nombre": "Portal SAT",
            "password_plain": "Secret#123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Empresa not found"


@pytest.mark.asyncio
async def test_boveda_permissions_for_tecnico_are_blocked(client: AsyncClient) -> None:
    admin_token = await _get_owner_admin_token(client)
    id_empresa = await _create_empresa(client, admin_token, "223456789")

    create_response = await client.post(
        "/api/v1/boveda/",
        json={
            "id_empresa": id_empresa,
            "nombre": "Servidor VPN",
            "password_plain": "Secret#123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    id_credencial = create_response.json()["id_credencial"]

    tecnico_token = await _create_user_and_login(
        client,
        admin_token,
        username="tecnico_boveda",
        email="tecnico_boveda@bigsolutions.pe",
        role="agente_soporte",
        id_cliente=id_empresa,
    )

    list_response = await client.get(
        "/api/v1/boveda/",
        headers={"Authorization": f"Bearer {tecnico_token}"},
    )
    assert list_response.status_code == 403

    reveal_response = await client.get(
        f"/api/v1/boveda/{id_credencial}/reveal",
        headers={"Authorization": f"Bearer {tecnico_token}"},
    )
    assert reveal_response.status_code == 403
    assert reveal_response.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_boveda_delete_is_superadmin_only(client: AsyncClient) -> None:
    admin_token = await _get_owner_admin_token(client)
    id_empresa = await _create_empresa(client, admin_token, "323456789")

    create_response = await client.post(
        "/api/v1/boveda/",
        json={
            "id_empresa": id_empresa,
            "nombre": "Intranet",
            "password_plain": "Secret#123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    id_credencial = create_response.json()["id_credencial"]

    ejecutivo_token = await _create_user_and_login(
        client,
        admin_token,
        username="ejecutivo_boveda",
        email="ejecutivo_boveda@bigsolutions.pe",
        role="ventas",
        id_cliente=id_empresa,
    )

    delete_response = await client.delete(
        f"/api/v1/boveda/{id_credencial}",
        headers={"Authorization": f"Bearer {ejecutivo_token}"},
    )
    assert delete_response.status_code == 403
