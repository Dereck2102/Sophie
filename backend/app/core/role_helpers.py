from __future__ import annotations

from fastapi import HTTPException

from app.infrastructure.models.usuario import RolEnum, Usuario


def assert_role_scope_by_tenant(
    target_tenant_id: int | None,
    target_role: RolEnum,
    enterprise_roles: tuple[RolEnum, ...],
) -> None:
    master_roles = {RolEnum.SUPERADMIN, RolEnum.ADMIN}
    if target_tenant_id is None:
        if target_role not in master_roles:
            raise HTTPException(
                status_code=400,
                detail="En el panel maestro solo se permiten roles superadmin y admin",
            )
        return

    if target_role not in enterprise_roles:
        raise HTTPException(
            status_code=400,
            detail="En el ERP solo se permiten roles: admin, agente_soporte, ventas, contable, rrhh y bodega",
        )


def assert_superadmin_only(
    current_user: Usuario,
    *,
    target_user: Usuario | None = None,
    target_role: RolEnum | None = None,
    target_tenant_id: int | None = None,
) -> None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return

    if target_user is not None and target_user.rol == RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede gestionar cuentas superadmin")
    if target_role == RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede asignar rol superadmin")

    target_is_master_panel = (
        (target_user is not None and target_user.id_cliente is None)
        or (target_tenant_id is None)
    )
    if target_is_master_panel:
        if target_user is not None and target_user.rol == RolEnum.ADMIN:
            raise HTTPException(status_code=403, detail="Solo el superadmin puede gestionar admin del panel maestro")
        if target_role == RolEnum.ADMIN:
            raise HTTPException(status_code=403, detail="Solo el superadmin puede asignar admin del panel maestro")


def assert_owner_superadmin_policy(
    current_user: Usuario,
    *,
    owner_superadmin_username: str,
    target_username: str,
    target_role: RolEnum,
    target_user: Usuario | None = None,
) -> None:
    owner_username = owner_superadmin_username.strip().lower()

    if current_user.rol == RolEnum.SUPERADMIN and current_user.username.lower() != owner_username:
        raise HTTPException(status_code=403, detail="Solo el superadmin propietario puede administrar cuentas")

    if target_role == RolEnum.SUPERADMIN and target_username.lower() != owner_username:
        raise HTTPException(
            status_code=403,
            detail=f"Solo '{owner_superadmin_username}' puede tener rol superadmin",
        )

    if target_user is not None and target_user.rol == RolEnum.SUPERADMIN and target_user.username.lower() != owner_username:
        raise HTTPException(status_code=403, detail="Cuenta superadmin inválida para esta política")

    if target_user is not None and target_user.username.lower() == owner_username and target_role != RolEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="No se puede degradar el superadmin propietario")