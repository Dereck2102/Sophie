from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.access import get_effective_access, has_access_item
from app.core.master_panel import is_master_admin_user, is_superadmin_user
from app.core.platform_catalog import get_plan_by_tier
from app.core.security import decode_token
from app.infrastructure.models.subscriptions import EmpresaSubscription, PlanTierEnum, SubscriptionStatusEnum
from app.infrastructure.models.usuario import RolEnum, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass(frozen=True)
class TenantContext:
    tenant_id: int
    role: RolEnum
    is_superadmin: bool


_MODULE_FEATURE_ALIASES: dict[str, set[str]] = {
    "usuarios": {"usuarios", "users", "E1"},
    "configuracion": {"configuracion", "settings", "E1"},
    "dashboard": {"dashboard", "E2", "dashboard_basic", "dashboard_advanced"},
    "ventas": {"ventas", "sales", "E4"},
    "cotizaciones": {"cotizaciones", "quotes", "E4"},
    "clientes": {"clientes", "crm", "E4"},
    "compras": {"compras", "purchases", "E5"},
    "inventario": {"inventario", "inventory", "E5", "inventory"},
    "proyectos": {"proyectos", "projects", "E6"},
    "tickets": {"tickets", "support", "E8"},
    "caja_chica": {"caja_chica", "petty_cash", "E3"},
    "caja_general": {"caja_general", "cash_closing", "E3"},
}


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

    if user.rol != RolEnum.SUPERADMIN and user.id_cliente is not None:
        sub_result = await db.execute(
            select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == user.id_cliente)
        )
        sub = sub_result.scalar_one_or_none()
        if sub and sub.status in {SubscriptionStatusEnum.CANCELED, SubscriptionStatusEnum.PAST_DUE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa está suspendida por estado de suscripción",
            )

    return user


def _extract_requested_tenant_id(request: Request) -> int | None:
    candidates = [
        request.path_params.get("empresa_id"),
        request.path_params.get("id_empresa"),
        request.path_params.get("tenant_id"),
        request.query_params.get("empresa_id"),
        request.query_params.get("id_empresa"),
        request.query_params.get("id_cliente"),
        request.query_params.get("tenant_id"),
    ]
    for raw_value in candidates:
        if raw_value is None:
            continue
        try:
            value = int(raw_value)
            if value > 0:
                return value
        except (TypeError, ValueError):
            continue
    return None


async def require_tenant_membership(
    request: Request,
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> TenantContext:
    requested_tenant_id = _extract_requested_tenant_id(request)

    user_tenant_id = current_user.id_cliente or current_user.id_empresa

    if is_superadmin_user(current_user):
        if requested_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id es obligatorio para rutas tenant",
            )
        return TenantContext(
            tenant_id=requested_tenant_id,
            role=current_user.rol,
            is_superadmin=True,
        )

    if user_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario no pertenece a una empresa",
        )

    effective_tenant_id = requested_tenant_id or user_tenant_id
    if effective_tenant_id != user_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a la empresa solicitada",
        )

    return TenantContext(
        tenant_id=effective_tenant_id,
        role=current_user.rol,
        is_superadmin=False,
    )


def _parse_feature_list(raw: str | None) -> set[str]:
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, list):
        return set()
    return {str(item).strip() for item in data if str(item).strip()}


def _module_enabled(features: set[str], module_key: str) -> bool:
    normalized_key = module_key.strip().lower()
    accepted = set(_MODULE_FEATURE_ALIASES.get(normalized_key, {module_key}))
    accepted.add(module_key)
    accepted.add(module_key.upper())
    return any(feature in features for feature in accepted)


def require_module_enabled(module_key: str):
    async def _checker(
        tenant_ctx: Annotated[TenantContext, Depends(require_tenant_membership)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> TenantContext:
        if tenant_ctx.is_superadmin:
            return tenant_ctx

        result = await db.execute(
            select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == tenant_ctx.tenant_id)
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            features = set(get_plan_by_tier(PlanTierEnum.STARTER).modules)
        else:
            if sub.status in {SubscriptionStatusEnum.CANCELED, SubscriptionStatusEnum.PAST_DUE}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="La empresa está suspendida por estado de suscripción",
                )

            custom_features = _parse_feature_list(sub.features_json)
            if custom_features:
                features = custom_features
            else:
                try:
                    features = set(get_plan_by_tier(sub.plan_tier).modules)
                except KeyError:
                    fallback_tier = sub.plan_tier if isinstance(sub.plan_tier, PlanTierEnum) else PlanTierEnum.STARTER
                    features = set(get_plan_by_tier(fallback_tier).modules)

        if not _module_enabled(features, module_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo deshabilitado para la empresa: {module_key}",
            )
        return tenant_ctx

    return _checker


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
        if is_superadmin_user(current_user):
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
        if is_superadmin_user(current_user):
            return current_user
        missing = [perm for perm in permissions if not has_access_item(effective_permissions, perm)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return current_user

    return _checker


def require_views(*views: str):
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        effective_views = getattr(current_user, "effective_views", [])
        if is_superadmin_user(current_user):
            return current_user
        missing = [view for view in views if not has_access_item(effective_views, view)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing views: {', '.join(missing)}",
            )
        return current_user

    return _checker


def require_superadmin():
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if not is_superadmin_user(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin only")
        return current_user

    return _checker


def require_master_admin():
    async def _checker(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if not is_master_admin_user(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Master admin access required")
        return current_user

    return _checker


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
