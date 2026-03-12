from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
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
)


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
    return list(result.scalars().all())


@router.post("/", response_model=UsuarioOut, status_code=201)
async def create_usuario(
    body: UsuarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> Usuario:
    await _validate_unique_identity(db, username=body.username, email=body.email)
    user = Usuario(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        rol=body.rol,
        nombre_completo=body.nombre_completo,
    )
    db.add(user)
    await db.flush()
    return user


@router.get("/me", response_model=UsuarioOut)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    return current_user


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
    return list(result.scalars().all())


@router.patch("/me", response_model=UsuarioOut)
async def update_my_profile(
    body: UsuarioSelfUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
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
    return current_user


@router.get("/{id_usuario}", response_model=UsuarioOut)
async def get_usuario(
    id_usuario: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> Usuario:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    return user


@router.patch("/{id_usuario}", response_model=UsuarioOut)
async def update_usuario(
    id_usuario: int,
    body: UsuarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> Usuario:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario not found")
    payload = body.model_dump(exclude_none=True)
    if "email" in payload:
        await _validate_unique_identity(db, email=payload["email"], exclude_user_id=id_usuario)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    await db.flush()
    return user


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
    await db.delete(user)
    await db.flush()
