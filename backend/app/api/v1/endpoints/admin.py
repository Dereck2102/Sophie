from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_superadmin
from app.core.access import dumps_json_list, get_effective_access
from app.core.database import get_db
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.sistema import ConfiguracionSistema
from app.infrastructure.models.usuario import Usuario
from app.schemas.usuario import (
    AuditoriaLogOut,
    BackupUsuariosIn,
    BackupUsuariosOut,
    BackupUsuarioItemOut,
    ConfiguracionSistemaOut,
    ConfiguracionSistemaUpdate,
    UsuarioOut,
)

router = APIRouter(prefix="/admin", tags=["Administración Global"])


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


async def _get_or_create_settings(db: AsyncSession) -> ConfiguracionSistema:
    result = await db.execute(select(ConfiguracionSistema).where(ConfiguracionSistema.id_configuracion == 1))
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    settings = ConfiguracionSistema(id_configuracion=1)
    db.add(settings)
    await db.flush()
    return settings


@router.get("/settings", response_model=ConfiguracionSistemaOut)
async def get_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> ConfiguracionSistema:
    return await _get_or_create_settings(db)


@router.get("/settings/public", response_model=ConfiguracionSistemaOut)
async def get_public_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfiguracionSistema:
    return await _get_or_create_settings(db)


@router.patch("/settings", response_model=ConfiguracionSistemaOut)
async def update_settings(
    body: ConfiguracionSistemaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> ConfiguracionSistema:
    settings = await _get_or_create_settings(db)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(settings, key, value)
    await db.flush()
    return settings


@router.get("/auditoria", response_model=list[AuditoriaLogOut])
async def list_auditoria(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    modulo: str | None = Query(None),
    id_usuario: int | None = Query(None),
) -> list[LogAuditoria]:
    query = select(LogAuditoria).order_by(LogAuditoria.fecha.desc()).offset(skip).limit(limit)
    if modulo:
        query = query.where(LogAuditoria.modulo == modulo)
    if id_usuario is not None:
        query = query.where(LogAuditoria.id_usuario == id_usuario)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/backup/usuarios", response_model=BackupUsuariosOut)
async def backup_usuarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> BackupUsuariosOut:
    settings = await _get_or_create_settings(db)
    result = await db.execute(select(Usuario).order_by(Usuario.id_usuario))
    users = result.scalars().all()
    return BackupUsuariosOut(
        generated_at=datetime.now(timezone.utc),
        settings=settings,
        users=[
            BackupUsuarioItemOut(
                username=user.username,
                email=user.email,
                password_hash=user.password_hash,
                rol=user.rol,
                nombre_completo=user.nombre_completo,
                activo=user.activo,
                mfa_habilitado=user.mfa_habilitado,
                force_mfa=user.force_mfa,
                foto_perfil_url=user.foto_perfil_url,
                email_verificado=user.email_verificado,
                permisos=get_effective_access(user)["permissions"],
                vistas=get_effective_access(user)["views"],
                herramientas=get_effective_access(user)["tools"],
            )
            for user in users
        ],
    )


@router.post("/restore/usuarios", status_code=status.HTTP_200_OK)
async def restore_usuarios(
    body: BackupUsuariosIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> dict[str, str]:
    if not body.users:
        raise HTTPException(status_code=400, detail="La copia debe incluir al menos un usuario")

    await db.execute(delete(Usuario))
    await db.flush()

    for item in body.users:
        user = Usuario(
            username=item.username,
            email=item.email,
            password_hash=item.password_hash,
            rol=item.rol,
            nombre_completo=item.nombre_completo,
            activo=item.activo,
            mfa_habilitado=item.mfa_habilitado,
            force_mfa=item.force_mfa,
            foto_perfil_url=item.foto_perfil_url,
            email_verificado=item.email_verificado,
            permisos_json=dumps_json_list(item.permisos),
            vistas_json=dumps_json_list(item.vistas),
            herramientas_json=dumps_json_list(item.herramientas),
        )
        db.add(user)

    settings = await _get_or_create_settings(db)
    if body.settings is not None:
        for key, value in body.settings.model_dump(exclude_none=True).items():
            setattr(settings, key, value)

    await db.flush()
    return {"detail": "Usuarios y configuración restaurados correctamente"}