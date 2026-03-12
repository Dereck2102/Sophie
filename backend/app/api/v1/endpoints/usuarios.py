from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
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
        current_user.email = body.email
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
