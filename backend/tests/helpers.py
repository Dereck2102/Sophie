"""
Helper that registers an admin user and returns an auth token.
Used by multiple test modules.
"""
from __future__ import annotations

from httpx import AsyncClient


async def get_admin_token(client: AsyncClient, suffix: str = "") -> str:
    """Register an admin and return the access token."""
    username = f"admin_{suffix}" if suffix else "admin_helper"
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@bigsolutions.pe",
            "password": "AdminPass123!",
            "rol": "admin",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]
