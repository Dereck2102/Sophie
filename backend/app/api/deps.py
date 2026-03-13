from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.access import get_effective_access, has_access_item
from app.core.security import decode_token
from app.infrastructure.models.usuario import RolEnum, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id_usuario == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.activo:
        raise credentials_exception
    access = get_effective_access(user)
    setattr(user, "effective_permissions", access["permissions"])
    setattr(user, "effective_views", access["views"])
    setattr(user, "effective_tools", access["tools"])
    return user


async def get_current_user_mfa_verified(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Like get_current_user but also requires MFA to be validated in this session."""
    user = await get_current_user(token, db)
    payload = decode_token(token)
    if user.mfa_habilitado and not payload.get("mfa_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA verification required for this resource",
        )
    return user


def require_roles(*roles: RolEnum):
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        # Superadmin siempre tiene permiso; otros deben estar en la lista de roles especificados
        if current_user.rol == RolEnum.SUPERADMIN:
            return current_user
        if current_user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


def require_permissions(*permissions: str):
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        effective_permissions = getattr(current_user, "effective_permissions", [])
        if current_user.rol == RolEnum.SUPERADMIN:
            return current_user
        missing = [perm for perm in permissions if not has_access_item(effective_permissions, perm)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return current_user

    return _checker


def require_superadmin():
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if current_user.rol != RolEnum.SUPERADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin only")
        return current_user

    return _checker


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
