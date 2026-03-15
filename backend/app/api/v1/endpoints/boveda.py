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
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.boveda import CredencialCreate, CredencialOut, CredencialUpdate, CredencialWithPassword

router = APIRouter(prefix="/boveda", tags=["Bóveda de Credenciales"])


@router.get("/", response_model=List[CredencialOut])
async def list_credenciales(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_views("boveda"))],
    authorized: Annotated[Usuario, Depends(require_permissions("boveda.manage"))],
) -> list[Credencial]:
    result = await db.execute(select(Credencial))
    return list(result.scalars().all())


@router.post("/", response_model=CredencialOut, status_code=201)
async def create_credencial(
    body: CredencialCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_views("boveda"))],
    authorized: Annotated[Usuario, Depends(require_permissions("boveda.manage"))],
) -> Credencial:
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
    return credencial


@router.get("/{id_credencial}/reveal", response_model=CredencialWithPassword)
async def reveal_credencial(
    id_credencial: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user_mfa_verified)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> CredencialWithPassword:
    """Requires MFA-verified session. Access is logged in audit log."""
    effective_permissions = getattr(current_user, "effective_permissions", [])
    effective_views = getattr(current_user, "effective_views", [])
    has_boveda_permission = "*" in effective_permissions or "boveda.manage" in effective_permissions
    has_boveda_view = "*" in effective_views or "boveda" in effective_views
    if current_user.rol != RolEnum.SUPERADMIN and (not has_boveda_permission or not has_boveda_view):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(Credencial).where(Credencial.id_credencial == id_credencial)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial not found")

    plain = decrypt_vault(cred.password_cifrado)

    db.add(
        LogAuditoria(
            id_usuario=current_user.id_usuario,
            accion="VAULT_ACCESS",
            modulo="boveda",
            ip_origen=ip,
            detalle={"id_credencial": id_credencial, "empresa": cred.id_empresa},
        )
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
    current_user: Annotated[Usuario, Depends(require_views("boveda"))],
    authorized: Annotated[Usuario, Depends(require_permissions("boveda.manage"))],
) -> Credencial:
    result = await db.execute(
        select(Credencial).where(Credencial.id_credencial == id_credencial)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial not found")
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
    await db.flush()
    return cred


@router.delete("/{id_credencial}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_credencial(
    id_credencial: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN))],
) -> None:
    result = await db.execute(
        select(Credencial).where(Credencial.id_credencial == id_credencial)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial not found")
    await db.delete(cred)
    await db.flush()
