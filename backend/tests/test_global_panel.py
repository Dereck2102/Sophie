from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.cliente import Cliente, Empresa, TipoClienteEnum
from app.infrastructure.models.proyectos import Proyecto
from app.infrastructure.models.usuario import RolEnum, Usuario


async def _seed_b2b_company(db_session: AsyncSession, suffix: str) -> tuple[int, int]:
    cliente = Cliente(tipo_cliente=TipoClienteEnum.B2B)
    db_session.add(cliente)
    await db_session.flush()

    empresa = Empresa(
        id_cliente=cliente.id_cliente,
        razon_social=f"Empresa {suffix}",
        ruc=f"179{suffix[:10]}",
        contacto_principal="QA",
    )
    db_session.add(empresa)
    await db_session.flush()
    return cliente.id_cliente, empresa.id_cliente


async def _create_user_and_login(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    suffix: str,
    rol: RolEnum,
    id_cliente: int | None = None,
    id_empresa: int | None = None,
    es_admin_global: bool = False,
) -> str:
    password = "TenantAdmin123!"
    user = Usuario(
        username=f"user_{suffix}",
        email=f"user_{suffix}@example.com",
        password_hash=hash_password(password),
        rol=rol,
        id_cliente=id_cliente,
        id_empresa=id_empresa,
        tipo_suscripcion="corporativa",
        es_admin_global=es_admin_global,
    )
    db_session.add(user)
    await db_session.flush()

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_global_ticket_lookups_return_clients_and_projects(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    suffix = uuid.uuid4().hex[:12]
    token = await _create_user_and_login(
        client,
        db_session,
        suffix=f"global_lookup_{suffix}",
        rol=RolEnum.AGENTE_SOPORTE,
        es_admin_global=True,
    )

    id_cliente, _ = await _seed_b2b_company(db_session, suffix)
    project = Proyecto(id_cliente=id_cliente, nombre=f"Proyecto {suffix}")
    db_session.add(project)
    await db_session.flush()

    clients_resp = await client.get(
        "/api/v1/global/tickets/lookups/clients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert clients_resp.status_code == 200
    clients_payload = clients_resp.json()
    target_client = next((item for item in clients_payload if item["id_cliente"] == id_cliente), None)
    assert target_client is not None
    assert target_client["empresa_nombre"] == f"Empresa {suffix}"

    projects_resp = await client.get(
        f"/api/v1/global/tickets/lookups/clients/{id_cliente}/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert projects_resp.status_code == 200
    projects_payload = projects_resp.json()
    assert any(item["id_proyecto"] == project.id_proyecto for item in projects_payload)


@pytest.mark.asyncio
async def test_admin_auditoria_is_forced_to_own_tenant_scope(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    suffix = uuid.uuid4().hex[:12]
    id_cliente_a, _ = await _seed_b2b_company(db_session, f"a{suffix}")
    id_cliente_b, _ = await _seed_b2b_company(db_session, f"b{suffix}")

    admin_user = Usuario(
        username=f"tenant_admin_{suffix}",
        email=f"tenant_admin_{suffix}@example.com",
        password_hash=hash_password("TenantAdmin123!"),
        rol=RolEnum.ADMIN,
        id_cliente=id_cliente_a,
        id_empresa=id_cliente_a,
        tipo_suscripcion="corporativa",
    )
    db_session.add(admin_user)
    await db_session.flush()

    db_session.add_all(
        [
            LogAuditoria(
                id_cliente=id_cliente_a,
                id_usuario=admin_user.id_usuario,
                accion="TENANT_A_EVENT",
                modulo="admin",
            ),
            LogAuditoria(
                id_cliente=id_cliente_b,
                id_usuario=admin_user.id_usuario,
                accion="TENANT_B_EVENT",
                modulo="admin",
            ),
        ]
    )
    await db_session.flush()

    token = await _create_user_and_login(
        client,
        db_session,
        suffix=f"tenant_admin_login_{suffix}",
        rol=RolEnum.ADMIN,
        id_cliente=id_cliente_a,
        id_empresa=id_cliente_a,
    )

    own_scope_resp = await client.get(
        "/api/v1/admin/auditoria",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert own_scope_resp.status_code == 200
    own_logs = own_scope_resp.json()
    assert own_logs
    assert all(log["id_cliente"] == id_cliente_a for log in own_logs)

    forbidden_resp = await client.get(
        f"/api/v1/admin/auditoria?id_cliente={id_cliente_b}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert forbidden_resp.status_code == 403
