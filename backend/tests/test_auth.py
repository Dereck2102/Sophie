from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """GET /health should return 200 with status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_first_admin(client: AsyncClient) -> None:
    """POST /api/v1/auth/register should create the first admin user."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "email": "admin@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "admin",
            "nombre_completo": "Administrador",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "admin"
    assert data["rol"] == "admin"
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
            "rol": "admin",
        },
    )
    # Second attempt
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin3",
            "email": "admin3@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "admin",
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
            "rol": "admin",
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
            "rol": "admin",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "badpass", "password": "WrongPass!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient) -> None:
    """GET /api/v1/usuarios/me should return the authenticated user."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "meuser",
            "email": "meuser@bigsolutions.pe",
            "password": "MePass123!",
            "rol": "admin",
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
