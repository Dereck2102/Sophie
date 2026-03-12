from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.access import dumps_json_list, get_effective_access
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioSelfUpdate, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

_ASSIGNABLE_ROLES = (
    RolEnum.TECNICO_TALLER,
    RolEnum.TECNICO_IT,
    RolEnum.CONSULTOR_SENIOR,
    RolEnum.ADMIN,
    RolEnum.SUPERADMIN,
)


def _serialize_user(user: Usuario) -> UsuarioOut:
    access = get_effective_access(user)
    return UsuarioOut(
        id_usuario=user.id_usuario,
        username=user.username,
        email=user.email,
        rol=user.rol,
        nombre_completo=user.nombre_completo,
        activo=user.activo,
        mfa_habilitado=user.mfa_habilitado,
        force_mfa=user.force_mfa,
        foto_perfil_url=user.foto_perfil_url,
        email_verificado=user.email_verificado,
        permisos=access["permissions"],
        vistas=access["views"],
        herramientas=access["tools"],
        fecha_creacion=user.fecha_creacion,
    )


def _assert_superadmin_only(current_user: Usuario, target_user: Usuario | None = None, target_role: RolEnum | None = None) -> None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return
    if target_user is not None and target_user.rol == RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede gestionar esta cuenta")
    if target_role == RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede asignar el rol superadmin")


async def _validate_unique_identity(
    db: AsyncSession,
    *,
    username: str | None = None,
    email: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    conditions = []
    if username is not None:
        conditions.append(Usuario.username == username)
    if email is not None:
        conditions.append(Usuario.email == email)
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


def _validate_profile_photo_data_url(photo_data_url: str | None) -> None:
    if photo_data_url is None:
        return
    if not photo_data_url.startswith("data:image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La foto debe enviarse como data URL de imagen válida",
        )
    if len(photo_data_url) > 2_500_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La foto excede el tamaño máximo permitido",
        )


@router.get("/", response_model=List[UsuarioOut])
async def list_usuarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Usuario]:
    result = await db.execute(select(Usuario).offset(skip).limit(limit))
    return [_serialize_user(user) for user in result.scalars().all()]


@router.post("/", response_model=UsuarioOut, status_code=201)
async def create_usuario(
    body: UsuarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> UsuarioOut:
    await _validate_unique_identity(db, username=body.username, email=body.email)
    _assert_superadmin_only(current_user, target_role=body.rol)
    user = Usuario(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        rol=body.rol,
        nombre_completo=body.nombre_completo,
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
    result = await db.execute(
        select(Usuario)
        .where(Usuario.activo.is_(True), Usuario.rol.in_(_ASSIGNABLE_ROLES))
        .order_by(Usuario.nombre_completo, Usuario.username)
    )
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
    if body.foto_perfil_url is not None:
        _validate_profile_photo_data_url(body.foto_perfil_url)
        current_user.foto_perfil_url = body.foto_perfil_url
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
    await db.flush()
    return _serialize_user(current_user)


@router.get("/{id_usuario}", response_model=UsuarioOut)
async def get_usuario(
    id_usuario: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> UsuarioOut:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    return _serialize_user(user)


@router.patch("/{id_usuario}", response_model=UsuarioOut)
async def update_usuario(
    id_usuario: int,
    body: UsuarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> UsuarioOut:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    _assert_superadmin_only(current_user, target_user=user, target_role=body.rol)
    payload = body.model_dump(exclude_none=True)
    if "email" in payload:
        await _validate_unique_identity(db, email=payload["email"], exclude_user_id=id_usuario)
    if "mfa_habilitado" in payload and current_user.rol != RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede cambiar MFA directamente")
    if "force_mfa" in payload and current_user.rol != RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede forzar MFA")

    permissions = payload.pop("permisos", None)
    views = payload.pop("vistas", None)
    tools = payload.pop("herramientas", None)
    for k, v in payload.items():
        setattr(user, k, v)
    if permissions is not None:
        if current_user.rol != RolEnum.SUPERADMIN:
            raise HTTPException(status_code=403, detail="Solo el superadmin puede cambiar permisos granulares")
        user.permisos_json = dumps_json_list(permissions)
    if views is not None:
        if current_user.rol != RolEnum.SUPERADMIN:
            raise HTTPException(status_code=403, detail="Solo el superadmin puede cambiar vistas")
        user.vistas_json = dumps_json_list(views)
    if tools is not None:
        if current_user.rol != RolEnum.SUPERADMIN:
            raise HTTPException(status_code=403, detail="Solo el superadmin puede cambiar herramientas")
        user.herramientas_json = dumps_json_list(tools)
    await db.flush()
    return _serialize_user(user)


@router.delete("/{id_usuario}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_usuario(
    id_usuario: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
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
    await db.delete(user)
    await db.flush()
