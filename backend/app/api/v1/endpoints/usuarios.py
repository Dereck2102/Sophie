from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.access import dumps_json_list, get_effective_access
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioSelfUpdate, UsuarioUpdate
from app.services.image_service import ImageOptimizationError, optimize_image

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
settings = get_settings()

_ASSIGNABLE_ROLES = (
    RolEnum.SUPERADMIN,
    RolEnum.ADMIN,
    RolEnum.JEFE_TECNOLOGIAS,
    RolEnum.JEFE_TALLER,
    RolEnum.JEFE_ADMINISTRATIVO,
    RolEnum.JEFE_CONTABLE,
    RolEnum.EJECUTIVO,
    RolEnum.ADMINISTRATIVO_CONTABLE,
    RolEnum.TECNICO,
    RolEnum.TECNICO_TALLER,
    RolEnum.AGENTE_SOPORTE_L1,
    RolEnum.AGENTE_SOPORTE_L2,
    RolEnum.DESARROLLADOR,
)

_PRIVILEGED_ROLES = (RolEnum.SUPERADMIN, RolEnum.ADMIN)
_ENTERPRISE_FIXED_ROLES = (
    RolEnum.ADMIN,
    RolEnum.AGENTE_SOPORTE_L1,
    RolEnum.ADMINISTRATIVO_CONTABLE,
)


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
            detail="En el ERP empresarial solo se permiten roles fijos: admin, soporte y ventas",
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
    user = Usuario(
        id_cliente=_resolve_target_tenant(current_user, getattr(body, "id_cliente", None)),
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
        payload["id_cliente"] = _resolve_target_tenant(current_user, requested_tenant)
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
