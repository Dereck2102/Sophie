from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_client_ip,
    get_current_user_mfa_verified,
    require_permissions,
    require_roles,
    require_views,
)
from app.core.database import get_db
from app.core.security import decrypt_vault, encrypt_vault
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.boveda import Credencial
from app.infrastructure.models.cliente import Empresa
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.boveda import CredencialCreate, CredencialOut, CredencialUpdate, CredencialWithPassword

router = APIRouter(prefix="/boveda", tags=["Bóveda de Credenciales"])


def _has_credential_access(user: Usuario) -> bool:
    effective_permissions = getattr(user, "effective_permissions", [])
    effective_views = getattr(user, "effective_views", [])
    has_permission = (
        "*" in effective_permissions
        or "empresas.manage" in effective_permissions
        or "boveda.manage" in effective_permissions
    )
    has_view = "*" in effective_views or "empresas" in effective_views or "boveda" in effective_views
    return user.rol == RolEnum.SUPERADMIN or (has_permission and has_view)


async def _get_credencial_or_404(db: AsyncSession, id_credencial: int) -> Credencial:
    result = await db.execute(select(Credencial).where(Credencial.id_credencial == id_credencial))
    credencial = result.scalar_one_or_none()
    if not credencial:
        raise HTTPException(status_code=404, detail="Credencial not found")
    return credencial


async def _assert_empresa_exists(db: AsyncSession, id_empresa: int) -> None:
    result = await db.execute(select(Empresa.id_cliente).where(Empresa.id_cliente == id_empresa))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Empresa not found")


def _audit_vault_event(
    *,
    db: AsyncSession,
    current_user: Usuario,
    ip: str,
    accion: str,
    credencial: Credencial,
) -> None:
    db.add(
        LogAuditoria(
            id_usuario=current_user.id_usuario,
            accion=accion,
            modulo="boveda",
            ip_origen=ip,
            detalle={"id_credencial": credencial.id_credencial, "empresa": credencial.id_empresa},
        )
    )


@router.get("/", response_model=List[CredencialOut])
async def list_credenciales(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Usuario, Depends(require_views("empresas"))],
    _authorized: Annotated[Usuario, Depends(require_permissions("empresas.manage"))],
) -> list[Credencial]:
    result = await db.execute(select(Credencial).order_by(Credencial.fecha_actualizacion.desc()))
    return list(result.scalars().all())


@router.post("/", response_model=CredencialOut, status_code=201)
async def create_credencial(
    body: CredencialCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_views("empresas"))],
    _authorized: Annotated[Usuario, Depends(require_permissions("empresas.manage"))],
    ip: Annotated[str, Depends(get_client_ip)],
) -> Credencial:
    await _assert_empresa_exists(db, body.id_empresa)

    credencial = Credencial(
        id_empresa=body.id_empresa,
        nombre=body.nombre,
        usuario_acceso=body.usuario_acceso,
        password_cifrado=encrypt_vault(body.password_plain),
        url=body.url,
        notas=body.notas,
    )
    db.add(credencial)
    await db.flush()

    _audit_vault_event(
        db=db,
        current_user=current_user,
        ip=ip,
        accion="VAULT_CREATE",
        credencial=credencial,
    )
    await db.flush()

    return credencial


@router.get("/{id_credencial}/reveal", response_model=CredencialWithPassword)
async def reveal_credencial(
    id_credencial: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user_mfa_verified)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> CredencialWithPassword:
    """Requires MFA-verified session. Access is logged in audit log."""
    if not _has_credential_access(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cred = await _get_credencial_or_404(db, id_credencial)

    plain = decrypt_vault(cred.password_cifrado)

    _audit_vault_event(
        db=db,
        current_user=current_user,
        ip=ip,
        accion="VAULT_ACCESS",
        credencial=cred,
    )
    await db.flush()

    return CredencialWithPassword(
        id_credencial=cred.id_credencial,
        id_empresa=cred.id_empresa,
        nombre=cred.nombre,
        usuario_acceso=cred.usuario_acceso,
        url=cred.url,
        notas=cred.notas,
        password_plain=plain,
    )


@router.patch("/{id_credencial}", response_model=CredencialOut)
async def update_credencial(
    id_credencial: int,
    body: CredencialUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_views("empresas"))],
    _authorized: Annotated[Usuario, Depends(require_permissions("empresas.manage"))],
    ip: Annotated[str, Depends(get_client_ip)],
) -> Credencial:
    cred = await _get_credencial_or_404(db, id_credencial)
    if body.nombre is not None:
        cred.nombre = body.nombre
    if body.usuario_acceso is not None:
        cred.usuario_acceso = body.usuario_acceso
    if body.password_plain is not None:
        cred.password_cifrado = encrypt_vault(body.password_plain)
    if body.url is not None:
        cred.url = body.url
    if body.notas is not None:
        cred.notas = body.notas

    _audit_vault_event(
        db=db,
        current_user=current_user,
        ip=ip,
        accion="VAULT_UPDATE",
        credencial=cred,
    )
    await db.flush()
    return cred


@router.delete("/{id_credencial}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_credencial(
    id_credencial: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN))],
    ip: Annotated[str, Depends(get_client_ip)],
) -> None:
    cred = await _get_credencial_or_404(db, id_credencial)

    _audit_vault_event(
        db=db,
        current_user=current_user,
        ip=ip,
        accion="VAULT_DELETE",
        credencial=cred,
    )
    await db.delete(cred)
    await db.flush()
