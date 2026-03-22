from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.access import dumps_json_list, get_effective_access
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.infrastructure.models.subscriptions import EmpresaSubscription, PlanTierEnum
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.usuario import (
    TenantStaffingBucketOut,
    TenantStaffingLimitsOut,
    UsuarioCreate,
    UsuarioOut,
    UsuarioSelfUpdate,
    UsuarioUpdate,
)
from app.services.image_service import ImageOptimizationError, optimize_image

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
settings = get_settings()

_ASSIGNABLE_ROLES = (
    RolEnum.SUPERADMIN,
    RolEnum.ADMIN,
    RolEnum.AGENTE_SOPORTE,
    RolEnum.VENTAS,
    RolEnum.CONTABLE,
    RolEnum.RRHH,
    RolEnum.BODEGA,
)

_PRIVILEGED_ROLES = (RolEnum.SUPERADMIN, RolEnum.ADMIN)
_ENTERPRISE_FIXED_ROLES = (
    RolEnum.ADMIN,
    RolEnum.AGENTE_SOPORTE,
    RolEnum.VENTAS,
    RolEnum.CONTABLE,
    RolEnum.RRHH,
    RolEnum.BODEGA,
)

_ROLE_AREA_MAP: dict[RolEnum, str] = {
    RolEnum.ADMIN: "direccion",
    RolEnum.AGENTE_SOPORTE: "soporte",
    RolEnum.VENTAS: "comercial",
    RolEnum.CONTABLE: "finanzas",
    RolEnum.RRHH: "personas",
    RolEnum.BODEGA: "operaciones",
}

_AREA_LABELS: dict[str, str] = {
    "direccion": "Dirección",
    "soporte": "Soporte",
    "comercial": "Comercial",
    "finanzas": "Finanzas",
    "personas": "Recursos Humanos",
    "operaciones": "Operaciones",
}

_PLAN_STAFFING_LIMITS: dict[PlanTierEnum, dict[str, object]] = {
    PlanTierEnum.STARTER: {
        "total_active_users": 6,
        "role_limits": {
            RolEnum.ADMIN.value: 1,
            RolEnum.AGENTE_SOPORTE.value: 1,
            RolEnum.VENTAS.value: 1,
            RolEnum.CONTABLE.value: 1,
            RolEnum.RRHH.value: 1,
            RolEnum.BODEGA.value: 1,
        },
        "area_limits": {"direccion": 1, "soporte": 1, "comercial": 1, "finanzas": 1, "personas": 1, "operaciones": 1},
    },
    PlanTierEnum.PRO: {
        "total_active_users": 24,
        "role_limits": {
            RolEnum.ADMIN.value: 4,
            RolEnum.AGENTE_SOPORTE.value: 6,
            RolEnum.VENTAS.value: 5,
            RolEnum.CONTABLE.value: 4,
            RolEnum.RRHH.value: 2,
            RolEnum.BODEGA.value: 3,
        },
        "area_limits": {"direccion": 4, "soporte": 6, "comercial": 5, "finanzas": 4, "personas": 2, "operaciones": 3},
    },
    PlanTierEnum.ENTERPRISE: {
        "total_active_users": 80,
        "role_limits": {
            RolEnum.ADMIN.value: 10,
            RolEnum.AGENTE_SOPORTE.value: 20,
            RolEnum.VENTAS.value: 15,
            RolEnum.CONTABLE.value: 12,
            RolEnum.RRHH.value: 8,
            RolEnum.BODEGA.value: 15,
        },
        "area_limits": {"direccion": 10, "soporte": 20, "comercial": 15, "finanzas": 12, "personas": 8, "operaciones": 15},
    },
    PlanTierEnum.CUSTOM: {
        "total_active_users": None,
        "role_limits": {},
        "area_limits": {},
    },
}


def _assert_same_tenant_or_superadmin(current_user: Usuario, target_user: Usuario) -> None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return
    if current_user.id_cliente is None:
        raise HTTPException(status_code=403, detail="Tu usuario no está asociado a un cliente")
    if target_user.id_cliente != current_user.id_cliente:
        raise HTTPException(status_code=403, detail="No puedes gestionar usuarios de otro cliente")


def _resolve_target_tenant(current_user: Usuario, requested_id_cliente: int | None) -> int | None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return requested_id_cliente
    if current_user.id_cliente is None:
        raise HTTPException(status_code=403, detail="Tu usuario no está asociado a un cliente")
    if requested_id_cliente is not None and requested_id_cliente != current_user.id_cliente:
        raise HTTPException(status_code=403, detail="No puedes asignar usuarios a otro cliente")
    return current_user.id_cliente


def _assert_enterprise_fixed_roles(current_user: Usuario, target_role: RolEnum | None) -> None:
    if target_role is None:
        return
    if current_user.rol == RolEnum.SUPERADMIN:
        return
    if target_role not in _ENTERPRISE_FIXED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="En el ERP solo se permiten roles: admin, agente_soporte, ventas, contable, rrhh y bodega",
        )


def _assert_role_scope_by_tenant(target_tenant_id: int | None, target_role: RolEnum) -> None:
    master_roles = {RolEnum.SUPERADMIN, RolEnum.ADMIN}
    if target_tenant_id is None:
        if target_role not in master_roles:
            raise HTTPException(
                status_code=400,
                detail="En el panel maestro solo se permiten roles superadmin y admin",
            )
        return

    if target_role not in _ENTERPRISE_FIXED_ROLES:
        raise HTTPException(
            status_code=400,
            detail="En el ERP solo se permiten roles: admin, agente_soporte, ventas, contable, rrhh y bodega",
        )


def _serialize_user(user: Usuario) -> UsuarioOut:
    access = get_effective_access(user)
    return UsuarioOut(
        id_usuario=user.id_usuario,
        id_cliente=user.id_cliente,
        username=user.username,
        email=user.email,
        rol=user.rol,
        nombre_completo=user.nombre_completo,
        telefono_recuperacion=user.telefono_recuperacion,
        activo=user.activo,
        mfa_habilitado=user.mfa_habilitado,
        force_mfa=user.force_mfa,
        foto_perfil_url=user.foto_perfil_url,
        email_verificado=user.email_verificado,
        telefono_verificado=user.telefono_verificado,
        permisos=access["permissions"],
        vistas=access["views"],
        herramientas=access["tools"],
        fecha_creacion=user.fecha_creacion,
    )


def _parse_feature_limits(raw_features: str | None) -> dict[str, int]:
    if not raw_features:
        return {}
    try:
        features = json.loads(raw_features)
    except json.JSONDecodeError:
        return {}
    if not isinstance(features, list):
        return {}

    parsed: dict[str, int] = {}
    for item in features:
        value = str(item).strip()
        if not value:
            continue
        if ":" not in value:
            continue
        key, _, raw_number = value.partition(":")
        number = raw_number.strip()
        if not number.isdigit():
            continue
        parsed[key.strip().lower()] = int(number)
    return parsed


async def _resolve_tenant_staffing_limits(
    db: AsyncSession,
    *,
    id_cliente: int,
) -> tuple[PlanTierEnum, dict[str, object]]:
    result = await db.execute(
        select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == id_cliente)
    )
    sub = result.scalar_one_or_none()
    plan_tier = sub.plan_tier if sub else PlanTierEnum.STARTER
    base = dict(_PLAN_STAFFING_LIMITS.get(plan_tier, _PLAN_STAFFING_LIMITS[PlanTierEnum.STARTER]))
    base_role_limits = dict(base.get("role_limits", {}))
    base_area_limits = dict(base.get("area_limits", {}))

    feature_limits = _parse_feature_limits(sub.features_json if sub else None)
    if "limit_total_users" in feature_limits:
        base["total_active_users"] = feature_limits["limit_total_users"]

    for role in _ENTERPRISE_FIXED_ROLES:
        role_key = f"limit_role_{role.value}"
        if role_key in feature_limits:
            base_role_limits[role.value] = feature_limits[role_key]

    for area_key in _AREA_LABELS:
        feature_key = f"limit_area_{area_key}"
        if feature_key in feature_limits:
            base_area_limits[area_key] = feature_limits[feature_key]

    base["role_limits"] = base_role_limits
    base["area_limits"] = base_area_limits
    return plan_tier, base


async def _tenant_active_counts(
    db: AsyncSession,
    *,
    id_cliente: int,
    exclude_user_id: int | None = None,
) -> tuple[int, dict[str, int], dict[str, int]]:
    query = (
        select(Usuario.rol, func.count(Usuario.id_usuario))
        .where(Usuario.id_cliente == id_cliente, Usuario.activo.is_(True))
        .group_by(Usuario.rol)
    )
    if exclude_user_id is not None:
        query = query.where(Usuario.id_usuario != exclude_user_id)

    result = await db.execute(query)
    by_role: dict[str, int] = {}
    by_area: dict[str, int] = {area: 0 for area in _AREA_LABELS}
    total = 0

    for role, count in result.all():
        role_key = role.value if isinstance(role, RolEnum) else str(role)
        count_int = int(count)
        by_role[role_key] = count_int
        total += count_int

        area_key = _ROLE_AREA_MAP.get(RolEnum(role_key)) if role_key in RolEnum._value2member_map_ else None
        if area_key:
            by_area[area_key] = by_area.get(area_key, 0) + count_int

    return total, by_role, by_area


def _remaining(limit_value: int | None, used: int) -> int | None:
    if limit_value is None:
        return None
    return max(limit_value - used, 0)


async def _assert_tenant_staffing_limits(
    db: AsyncSession,
    *,
    id_cliente: int | None,
    target_role: RolEnum,
    exclude_user_id: int | None = None,
) -> None:
    if id_cliente is None:
        return
    if target_role not in _ENTERPRISE_FIXED_ROLES:
        return

    _, limits = await _resolve_tenant_staffing_limits(db, id_cliente=id_cliente)
    total, by_role, by_area = await _tenant_active_counts(db, id_cliente=id_cliente, exclude_user_id=exclude_user_id)

    total_limit = limits.get("total_active_users")
    if isinstance(total_limit, int) and total + 1 > total_limit:
        raise HTTPException(
            status_code=409,
            detail=f"Límite del plan alcanzado: máximo {total_limit} usuarios activos para esta empresa",
        )

    role_limits: dict[str, int] = limits.get("role_limits", {})  # type: ignore[assignment]
    role_key = target_role.value
    if role_key in role_limits and by_role.get(role_key, 0) + 1 > role_limits[role_key]:
        raise HTTPException(
            status_code=409,
            detail=f"Límite por rol alcanzado ({target_role.value}): máximo {role_limits[role_key]} usuarios",
        )

    area_key = _ROLE_AREA_MAP.get(target_role)
    area_limits: dict[str, int] = limits.get("area_limits", {})  # type: ignore[assignment]
    if area_key and area_key in area_limits and by_area.get(area_key, 0) + 1 > area_limits[area_key]:
        raise HTTPException(
            status_code=409,
            detail=f"Límite por área alcanzado ({_AREA_LABELS.get(area_key, area_key)}): máximo {area_limits[area_key]} usuarios",
        )


def _build_staffing_response(
    *,
    id_cliente: int,
    plan_tier: PlanTierEnum,
    limits: dict[str, object],
    total_used: int,
    by_role_used: dict[str, int],
    by_area_used: dict[str, int],
) -> TenantStaffingLimitsOut:
    role_limits = limits.get("role_limits", {})
    area_limits = limits.get("area_limits", {})
    total_limit = limits.get("total_active_users")

    roles_out: list[TenantStaffingBucketOut] = []
    for role in _ENTERPRISE_FIXED_ROLES:
        role_key = role.value
        role_limit = role_limits.get(role_key) if isinstance(role_limits, dict) else None
        role_used = by_role_used.get(role_key, 0)
        roles_out.append(
            TenantStaffingBucketOut(
                key=role_key,
                label=role_key,
                limit=role_limit if isinstance(role_limit, int) else None,
                used=role_used,
                remaining=_remaining(role_limit if isinstance(role_limit, int) else None, role_used),
            )
        )

    areas_out: list[TenantStaffingBucketOut] = []
    for area_key, area_label in _AREA_LABELS.items():
        area_limit = area_limits.get(area_key) if isinstance(area_limits, dict) else None
        area_used = by_area_used.get(area_key, 0)
        areas_out.append(
            TenantStaffingBucketOut(
                key=area_key,
                label=area_label,
                limit=area_limit if isinstance(area_limit, int) else None,
                used=area_used,
                remaining=_remaining(area_limit if isinstance(area_limit, int) else None, area_used),
            )
        )

    total_limit_int = total_limit if isinstance(total_limit, int) else None
    return TenantStaffingLimitsOut(
        id_cliente=id_cliente,
        plan_tier=plan_tier.value,
        total_limit=total_limit_int,
        total_used=total_used,
        total_remaining=_remaining(total_limit_int, total_used),
        by_role=roles_out,
        by_area=areas_out,
    )


def _assert_superadmin_only(current_user: Usuario, target_user: Usuario | None = None, target_role: RolEnum | None = None) -> None:
    """Ensures privileged-role accounts can only be managed by superadmin;
    admin users cannot manage other admin/superadmin accounts."""
    if current_user.rol == RolEnum.SUPERADMIN:
        return  # Superadmin can manage anyone (further checked by owner policy)
    _protected = (RolEnum.SUPERADMIN, RolEnum.ADMIN)
    if target_user is not None and target_user.rol in _protected:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede gestionar cuentas de administrador")
    if target_role in _protected:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede asignar roles de administrador")


def _owner_superadmin_username() -> str:
    return settings.OWNER_SUPERADMIN_USERNAME.strip().lower()


def _assert_owner_superadmin_policy(
    current_user: Usuario,
    *,
    target_username: str,
    target_role: RolEnum,
    target_user: Usuario | None = None,
) -> None:
    owner_username = _owner_superadmin_username()
    if current_user.rol == RolEnum.SUPERADMIN and current_user.username.lower() != owner_username:
        raise HTTPException(status_code=403, detail="Solo el superadmin propietario puede administrar cuentas")

    if target_role == RolEnum.SUPERADMIN and target_username.lower() != owner_username:
        raise HTTPException(
            status_code=403,
            detail=f"Solo '{settings.OWNER_SUPERADMIN_USERNAME}' puede tener rol superadmin",
        )

    if target_user is not None and target_user.rol == RolEnum.SUPERADMIN and target_user.username.lower() != owner_username:
        raise HTTPException(status_code=403, detail="Cuenta superadmin inválida para esta política")

    if (
        target_user is not None
        and target_user.username.lower() == owner_username
        and target_role != RolEnum.SUPERADMIN
    ):
        raise HTTPException(status_code=403, detail="No se puede degradar el superadmin propietario")


async def _validate_unique_identity(
    db: AsyncSession,
    *,
    username: str | None = None,
    email: str | None = None,
    telefono_recuperacion: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    conditions = []
    if username is not None:
        conditions.append(Usuario.username == username)
    if email is not None:
        conditions.append(Usuario.email == email)
    if telefono_recuperacion is not None:
        conditions.append(Usuario.telefono_recuperacion == telefono_recuperacion)
    if not conditions:
        return

    query = select(Usuario).where(or_(*conditions))
    if exclude_user_id is not None:
        query = query.where(Usuario.id_usuario != exclude_user_id)

    existing_result = await db.execute(query)
    existing = existing_result.scalars().all()
    for user in existing:
        if username is not None and user.username == username:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        if email is not None and user.email == email:
            raise HTTPException(status_code=400, detail="El correo ya está registrado")
        if telefono_recuperacion is not None and user.telefono_recuperacion == telefono_recuperacion:
            raise HTTPException(status_code=400, detail="El teléfono de recuperación ya está registrado")


def _validate_and_optimize_photo(photo_data_url: str | None) -> str | None:
    """Valida y optimiza automáticamente una foto de perfil."""
    if photo_data_url is None:
        return None
    if not photo_data_url.startswith("data:image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La foto debe enviarse como data URL de imagen válida",
        )
    try:
        return optimize_image(photo_data_url, image_type="profile", target_width=400)
    except ImageOptimizationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando imagen: {e}",
        )


@router.get("/", response_model=List[UsuarioOut])
async def list_usuarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Usuario]:
    query = select(Usuario)
    if current_user.rol != RolEnum.SUPERADMIN and current_user.id_cliente is not None:
        query = query.where(Usuario.id_cliente == current_user.id_cliente)
    result = await db.execute(query.offset(skip).limit(limit))
    return [_serialize_user(user) for user in result.scalars().all()]


@router.post("/", response_model=UsuarioOut, status_code=201)
async def create_usuario(
    body: UsuarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
) -> UsuarioOut:
    await _validate_unique_identity(
        db,
        username=body.username,
        email=body.email,
        telefono_recuperacion=body.telefono_recuperacion,
    )
    _assert_superadmin_only(current_user, target_role=body.rol)
    _assert_enterprise_fixed_roles(current_user, body.rol)
    _assert_owner_superadmin_policy(
        current_user,
        target_username=body.username,
        target_role=body.rol,
    )
    target_tenant_id = _resolve_target_tenant(current_user, getattr(body, "id_cliente", None))
    _assert_role_scope_by_tenant(target_tenant_id, body.rol)
    await _assert_tenant_staffing_limits(
        db,
        id_cliente=target_tenant_id,
        target_role=body.rol,
    )
    user = Usuario(
        id_cliente=target_tenant_id,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        rol=body.rol,
        nombre_completo=body.nombre_completo,
        telefono_recuperacion=body.telefono_recuperacion,
        mfa_habilitado=body.mfa_habilitado if body.mfa_habilitado is not None else False,
        force_mfa=body.force_mfa if body.force_mfa is not None else False,
        permisos_json=dumps_json_list(getattr(body, "permisos", None)),
        vistas_json=dumps_json_list(getattr(body, "vistas", None)),
        herramientas_json=dumps_json_list(getattr(body, "herramientas", None)),
    )
    db.add(user)
    await db.flush()
    return _serialize_user(user)


@router.get("/me", response_model=UsuarioOut)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    return _serialize_user(current_user)


@router.get("/capacidad", response_model=TenantStaffingLimitsOut)
async def get_tenant_staffing_capacity(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
    id_cliente: int | None = Query(None, ge=1),
) -> TenantStaffingLimitsOut:
    tenant_id = _resolve_target_tenant(current_user, id_cliente)
    if tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Debes indicar id_cliente para consultar capacidad cuando no estás asociado a una empresa",
        )

    plan_tier, limits = await _resolve_tenant_staffing_limits(db, id_cliente=tenant_id)
    total_used, by_role_used, by_area_used = await _tenant_active_counts(db, id_cliente=tenant_id)
    return _build_staffing_response(
        id_cliente=tenant_id,
        plan_tier=plan_tier,
        limits=limits,
        total_used=total_used,
        by_role_used=by_role_used,
        by_area_used=by_area_used,
    )


@router.get("/asignables", response_model=List[UsuarioOut])
async def list_assignable_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[Usuario]:
    query = (
        select(Usuario)
        .where(Usuario.activo.is_(True), Usuario.rol.in_(_ASSIGNABLE_ROLES))
        .order_by(Usuario.nombre_completo, Usuario.username)
    )
    if current_user.rol != RolEnum.SUPERADMIN and current_user.id_cliente is not None:
        query = query.where(Usuario.id_cliente == current_user.id_cliente)
        query = query.where(Usuario.rol.in_(_ENTERPRISE_FIXED_ROLES))
    result = await db.execute(query)
    return [_serialize_user(user) for user in result.scalars().all()]


@router.patch("/me", response_model=UsuarioOut)
async def update_my_profile(
    body: UsuarioSelfUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UsuarioOut:
    if body.nombre_completo is not None:
        current_user.nombre_completo = body.nombre_completo
    if body.email is not None:
        await _validate_unique_identity(
            db,
            email=body.email,
            exclude_user_id=current_user.id_usuario,
        )
        if body.email != current_user.email:
            current_user.email_verificado = False
            current_user.email_verificacion_token = secrets.token_urlsafe(24)
            current_user.email_verificacion_expira = datetime.now(timezone.utc) + timedelta(hours=24)
        current_user.email = body.email
    if body.telefono_recuperacion is not None:
        await _validate_unique_identity(
            db,
            telefono_recuperacion=body.telefono_recuperacion,
            exclude_user_id=current_user.id_usuario,
        )
        current_user.telefono_recuperacion = body.telefono_recuperacion
        current_user.telefono_verificado = False
    if body.foto_perfil_url is not None:
        current_user.foto_perfil_url = _validate_and_optimize_photo(body.foto_perfil_url)
    if body.new_password is not None:
        if not body.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="current_password is required to set a new password",
            )
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar la contraseña. Verifica tus credenciales.",
            )
        current_user.password_hash = hash_password(body.new_password)
        current_user.refresh_token_version = int(current_user.refresh_token_version or 1) + 1
        current_user.ultima_rotacion_password = datetime.now(timezone.utc)
    await db.flush()
    return _serialize_user(current_user)


@router.get("/{id_usuario}", response_model=UsuarioOut)
async def get_usuario(
    id_usuario: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
) -> UsuarioOut:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    _assert_same_tenant_or_superadmin(current_user, user)
    return _serialize_user(user)


@router.patch("/{id_usuario}", response_model=UsuarioOut)
async def update_usuario(
    id_usuario: int,
    body: UsuarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
) -> UsuarioOut:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    _assert_same_tenant_or_superadmin(current_user, user)
    _assert_superadmin_only(current_user, target_user=user, target_role=body.rol)
    _assert_enterprise_fixed_roles(current_user, body.rol)
    effective_role = body.rol if body.rol is not None else user.rol
    _assert_owner_superadmin_policy(
        current_user,
        target_username=user.username,
        target_role=effective_role,
        target_user=user,
    )
    payload = body.model_dump(exclude_none=True)
    requested_tenant = payload.get("id_cliente")
    effective_tenant_id = user.id_cliente if requested_tenant is None else _resolve_target_tenant(current_user, requested_tenant)
    effective_active = payload.get("activo", user.activo)
    _assert_role_scope_by_tenant(effective_tenant_id, effective_role)
    if effective_active:
        await _assert_tenant_staffing_limits(
            db,
            id_cliente=effective_tenant_id,
            target_role=effective_role,
            exclude_user_id=user.id_usuario,
        )
    if "email" in payload:
        await _validate_unique_identity(db, email=payload["email"], exclude_user_id=id_usuario)
    if "telefono_recuperacion" in payload:
        await _validate_unique_identity(
            db,
            telefono_recuperacion=payload["telefono_recuperacion"],
            exclude_user_id=id_usuario,
        )
    _is_privileged = current_user.rol in _PRIVILEGED_ROLES
    if "mfa_habilitado" in payload and not _is_privileged:
        raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar MFA directamente")
    if "force_mfa" in payload and not _is_privileged:
        raise HTTPException(status_code=403, detail="Solo administradores pueden forzar MFA")

    permissions = payload.pop("permisos", None)
    views = payload.pop("vistas", None)
    tools = payload.pop("herramientas", None)
    requested_tenant = payload.pop("id_cliente", None)
    if requested_tenant is not None:
        payload["id_cliente"] = effective_tenant_id
    for k, v in payload.items():
        setattr(user, k, v)
    if permissions is not None:
        if not _is_privileged:
            raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar permisos granulares")
        user.permisos_json = dumps_json_list(permissions)
    if views is not None:
        if not _is_privileged:
            raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar vistas")
        user.vistas_json = dumps_json_list(views)
    if tools is not None:
        if not _is_privileged:
            raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar herramientas")
        user.herramientas_json = dumps_json_list(tools)
    await db.flush()
    return _serialize_user(user)


@router.delete("/{id_usuario}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_usuario(
    id_usuario: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
) -> None:
    if current_user.id_usuario == id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta administradora desde esta vista",
        )

    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    _assert_superadmin_only(current_user, target_user=user)
    _assert_owner_superadmin_policy(
        current_user,
        target_username=user.username,
        target_role=user.rol,
        target_user=user,
    )
    await db.delete(user)
    await db.flush()
