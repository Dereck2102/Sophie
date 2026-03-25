from __future__ import annotations

from app.infrastructure.models.usuario import RolEnum, Usuario

MASTER_ADMIN_ROLES: tuple[RolEnum, ...] = (RolEnum.SUPERADMIN, RolEnum.ADMIN)


def is_superadmin_user(user: Usuario) -> bool:
    return user.rol == RolEnum.SUPERADMIN


def is_master_admin_user(user: Usuario) -> bool:
    return user.id_cliente is None and user.rol in MASTER_ADMIN_ROLES