from __future__ import annotations

import pytest
import pytest_asyncio
import pyotp
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import auth as auth_endpoints
from app.infrastructure.models.auditoria import LogAuditoria


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """GET /health should return 200 with status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_first_admin(client: AsyncClient) -> None:
    """POST /api/v1/auth/register should bootstrap the first superadmin user."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "email": "admin@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "superadmin",
            "nombre_completo": "Administrador",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "admin"
    assert data["rol"] == "superadmin"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_second_admin_blocked(client: AsyncClient) -> None:
    """Second register attempt must be rejected (403)."""
    # First registration
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin2",
            "email": "admin2@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "superadmin",
        },
    )
    # Second attempt
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin3",
            "email": "admin3@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "superadmin",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Correct credentials should return an access token."""
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@bigsolutions.pe",
            "password": "TestPass123!",
            "rol": "superadmin",
        },
    )
    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "TestPass123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["access_token"] != ""


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """Wrong password should return 401."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "badpass",
            "email": "badpass@bigsolutions.pe",
            "password": "RealPass123!",
            "rol": "superadmin",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "badpass", "password": "WrongPass!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_lockout_after_failed_attempts(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "lock_user",
            "email": "lock_user@bigsolutions.pe",
            "password": "LockPass123!",
            "rol": "superadmin",
        },
    )

    for _ in range(5):
        wrong = await client.post(
            "/api/v1/auth/login",
            json={"username": "lock_user", "password": "WrongPass!"},
        )
        assert wrong.status_code == 401

    locked = await client.post(
        "/api/v1/auth/login",
        json={"username": "lock_user", "password": "LockPass123!"},
    )
    assert locked.status_code == 423


@pytest.mark.asyncio
async def test_login_failed_writes_audit_log(client: AsyncClient, db_session: AsyncSession) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "audit_fail",
            "email": "audit_fail@bigsolutions.pe",
            "password": "RealPass123!",
            "rol": "superadmin",
        },
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "audit_fail", "password": "WrongPass!"},
    )
    assert resp.status_code == 401

    log_result = await db_session.execute(
        select(LogAuditoria).where(
            LogAuditoria.modulo == "auth",
            LogAuditoria.accion == "LOGIN_FAILED",
        )
    )
    logs = list(log_result.scalars().all())
    assert logs
    assert any((log.detalle or {}).get("username") == "audit_fail" for log in logs)


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient) -> None:
    """GET /api/v1/usuarios/me should return the authenticated user."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "meuser",
            "email": "meuser@bigsolutions.pe",
            "password": "MePass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "meuser", "password": "MePass123!"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/usuarios/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_refresh_uses_cookie_when_body_missing(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "cookie_refresh",
            "email": "cookie_refresh@bigsolutions.pe",
            "password": "CookiePass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "cookie_refresh", "password": "CookiePass123!"},
    )
    assert login.status_code == 200

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json().get("access_token")


@pytest.mark.asyncio
async def test_refresh_token_replay_is_rejected(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "refresh_replay",
            "email": "refresh_replay@bigsolutions.pe",
            "password": "ReplayPass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "refresh_replay", "password": "ReplayPass123!"},
    )
    assert login.status_code == 200

    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first_refresh.status_code == 200

    replay_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_refresh.status_code == 401


@pytest.mark.asyncio
async def test_email_verification_token_flow(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "mail_verify",
            "email": "mail_verify@bigsolutions.pe",
            "password": "MailPass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "mail_verify", "password": "MailPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    req = await client.post("/api/v1/auth/email/verification-token", headers=headers)
    assert req.status_code == 200
    verification_token = req.json().get("token")
    assert verification_token

    verify = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
        headers=headers,
    )
    assert verify.status_code == 200

    me = await client.get("/api/v1/usuarios/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email_verificado"] is True


@pytest.mark.asyncio
async def test_update_profile_rejects_invalid_photo_data(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "photo_invalid",
            "email": "photo_invalid@bigsolutions.pe",
            "password": "PhotoPass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "photo_invalid", "password": "PhotoPass123!"},
    )
    token = login.json()["access_token"]

    resp = await client.patch(
        "/api/v1/usuarios/me",
        json={"foto_perfil_url": "https://example.com/photo.png"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_usuario_rejects_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "damacoria",
            "email": "damacoria@bigsolutions.pe",
            "password": "OwnerPass123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "damacoria", "password": "OwnerPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_1 = await client.post(
        "/api/v1/usuarios/",
        json={
            "username": "vendedor_1",
            "email": "duplicado@bigsolutions.pe",
            "password": "VendPass123!",
            "rol": "admin",
        },
        headers=headers,
    )
    assert create_1.status_code == 201

    create_2 = await client.post(
        "/api/v1/usuarios/",
        json={
            "username": "vendedor_2",
            "email": "duplicado@bigsolutions.pe",
            "password": "VendPass123!",
            "rol": "admin",
        },
        headers=headers,
    )
    assert create_2.status_code == 400


@pytest.mark.asyncio
async def test_password_recovery_flow_rotates_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "recover_user",
            "email": "recover_user@bigsolutions.pe",
            "password": "RecoverPass123!",
            "rol": "superadmin",
        },
    )

    original_debug = auth_endpoints.settings.DEBUG
    auth_endpoints.settings.DEBUG = True
    try:
        request_resp = await client.post(
            "/api/v1/auth/password-recovery/request",
            json={"identifier": "recover_user@bigsolutions.pe"},
        )
        assert request_resp.status_code == 200
        token = request_resp.json().get("recovery_token")
        assert token
    finally:
        auth_endpoints.settings.DEBUG = original_debug

    confirm_resp = await client.post(
        "/api/v1/auth/password-recovery/confirm",
        json={"token": token, "new_password": "RecoverPass456!"},
    )
    assert confirm_resp.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "recover_user", "password": "RecoverPass123!"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "recover_user", "password": "RecoverPass456!"},
    )
    assert new_login.status_code == 200
    assert new_login.json().get("access_token")


@pytest.mark.asyncio
async def test_login_with_mfa_recovery_code(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "recovery_mfa",
            "email": "recovery_mfa@bigsolutions.pe",
            "password": "RecoveryMfa123!",
            "rol": "superadmin",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "recovery_mfa", "password": "RecoveryMfa123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    setup_resp = await client.get("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json().get("secret")
    assert secret

    code = pyotp.TOTP(secret).now()
    verify_resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": code},
        headers=headers,
    )
    assert verify_resp.status_code == 200

    rotate_resp = await client.post(
        "/api/v1/auth/mfa/recovery-codes/rotate",
        json={"current_password": "RecoveryMfa123!"},
        headers=headers,
    )
    assert rotate_resp.status_code == 200
    recovery_codes = rotate_resp.json().get("codes")
    assert isinstance(recovery_codes, list)
    assert len(recovery_codes) == 8

    login_with_recovery = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "recovery_mfa",
            "password": "RecoveryMfa123!",
            "recovery_code": recovery_codes[0],
        },
    )
    assert login_with_recovery.status_code == 200
    assert login_with_recovery.json().get("access_token")


@pytest.mark.asyncio
async def test_tenant_starter_limits_one_specialist_per_role(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "damacoria",
            "email": "damacoria@bigsolutions.pe",
            "password": "OwnerPass123!",
            "rol": "superadmin",
        },
    )
    super_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "damacoria", "password": "OwnerPass123!"},
    )
    super_headers = {"Authorization": f"Bearer {super_login.json()['access_token']}"}

    empresa_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Limites Starter",
                "ruc": "20999900001",
                "contacto_principal": "Juan Base",
                "telefono": "0999000111",
                "email": "starter_limits@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_resp.status_code == 201
    tenant_id = empresa_resp.json()["id_cliente"]

    tenant_admin_resp = await client.post(
        "/api/v1/usuarios/",
        json={
            "id_cliente": tenant_id,
            "username": "tenant_admin",
            "email": "tenant_admin@bigsolutions.pe",
            "password": "TenantAdmin123!",
            "rol": "admin",
        },
        headers=super_headers,
    )
    assert tenant_admin_resp.status_code == 201

    tenant_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "tenant_admin", "password": "TenantAdmin123!"},
    )
    tenant_headers = {"Authorization": f"Bearer {tenant_login.json()['access_token']}"}

    support_1 = await client.post(
        "/api/v1/usuarios/",
        json={
            "username": "support_one",
            "email": "support_one@bigsolutions.pe",
            "password": "Support123!",
            "rol": "agente_soporte",
        },
        headers=tenant_headers,
    )
    assert support_1.status_code == 201

    support_2 = await client.post(
        "/api/v1/usuarios/",
        json={
            "username": "support_two",
            "email": "support_two@bigsolutions.pe",
            "password": "Support123!",
            "rol": "agente_soporte",
        },
        headers=tenant_headers,
    )
    assert support_2.status_code == 409
    assert "Límite por rol" in support_2.json().get("detail", "")


@pytest.mark.asyncio
async def test_tenant_capacity_endpoint_returns_area_and_role_buckets(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "damacoria",
            "email": "damacoria@bigsolutions.pe",
            "password": "OwnerPass123!",
            "rol": "superadmin",
        },
    )
    super_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "damacoria", "password": "OwnerPass123!"},
    )
    super_headers = {"Authorization": f"Bearer {super_login.json()['access_token']}"}

    empresa_resp = await client.post(
        "/api/v1/clientes/",
        json={
            "tipo_cliente": "B2B",
            "estado": "activo",
            "empresa": {
                "razon_social": "Empresa Capacity",
                "ruc": "20999900002",
                "contacto_principal": "Maria Ops",
                "telefono": "0999000222",
                "email": "capacity@bigsolutions.pe",
            },
        },
        headers=super_headers,
    )
    assert empresa_resp.status_code == 201
    tenant_id = empresa_resp.json()["id_cliente"]

    await client.post(
        "/api/v1/usuarios/",
        json={
            "id_cliente": tenant_id,
            "username": "admin_capacity",
            "email": "admin_capacity@bigsolutions.pe",
            "password": "AdminCap123!",
            "rol": "admin",
        },
        headers=super_headers,
    )

    tenant_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_capacity", "password": "AdminCap123!"},
    )
    tenant_headers = {"Authorization": f"Bearer {tenant_login.json()['access_token']}"}

    capacity_resp = await client.get("/api/v1/usuarios/capacidad", headers=tenant_headers)
    assert capacity_resp.status_code == 200
    payload = capacity_resp.json()

    assert payload["id_cliente"] == tenant_id
    assert payload["plan_tier"] == "starter"
    assert payload["total_limit"] == 6
    assert payload["total_used"] == 1
    assert isinstance(payload["by_role"], list)
    assert isinstance(payload["by_area"], list)
    assert any(item["key"] == "admin" and item["used"] == 1 for item in payload["by_role"])
    assert any(item["key"] == "direccion" and item["used"] == 1 for item in payload["by_area"])
