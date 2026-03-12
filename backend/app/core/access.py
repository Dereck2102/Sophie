from __future__ import annotations

import json

from app.infrastructure.models.usuario import RolEnum, Usuario

ROLE_ACCESS: dict[RolEnum, dict[str, list[str]]] = {
    RolEnum.SUPERADMIN: {
        "permissions": ["*"],
        "views": ["*"],
        "tools": ["*"],
    },
    RolEnum.ADMIN: {
        "permissions": [
            "usuarios.manage",
            "clientes.manage",
            "ventas.manage",
            "tickets.manage",
            "inventario.manage",
            "compras.manage",
            "proyectos.manage",
            "dashboard.view",
            "boveda.manage",
            "configuracion.manage",
        ],
        "views": [
            "dashboard",
            "crm",
            "ventas",
            "compras",
            "taller",
            "proyectos",
            "boveda",
            "usuarios",
            "configuracion",
            "perfil",
        ],
        "tools": ["reportes", "exportaciones", "ajustes"],
    },
    RolEnum.EJECUTIVO: {
        "permissions": ["dashboard.view", "clientes.manage", "ventas.manage", "tickets.manage"],
        "views": ["dashboard", "crm", "ventas", "taller", "perfil"],
        "tools": ["reportes"],
    },
    RolEnum.ADMINISTRATIVO_CONTABLE: {
        "permissions": ["dashboard.view", "compras.manage", "ventas.manage", "clientes.manage"],
        "views": ["dashboard", "crm", "ventas", "compras", "perfil"],
        "tools": ["reportes", "exportaciones"],
    },
    RolEnum.VENDEDOR: {
        "permissions": ["dashboard.view", "clientes.manage", "ventas.manage"],
        "views": ["dashboard", "crm", "ventas", "perfil"],
        "tools": ["reportes"],
    },
    RolEnum.TECNICO_TALLER: {
        "permissions": ["dashboard.view", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "taller", "perfil"],
        "tools": ["diagnostico"],
    },
    RolEnum.TECNICO_IT: {
        "permissions": ["dashboard.view", "tickets.manage", "boveda.read"],
        "views": ["dashboard", "taller", "boveda", "perfil"],
        "tools": ["diagnostico", "credenciales"],
    },
    RolEnum.COMPRADOR: {
        "permissions": ["dashboard.view", "compras.manage", "inventario.manage"],
        "views": ["dashboard", "compras", "perfil"],
        "tools": ["exportaciones"],
    },
    RolEnum.DESARROLLADOR: {
        "permissions": ["dashboard.view", "proyectos.manage", "tickets.manage"],
        "views": ["dashboard", "proyectos", "taller", "perfil"],
        "tools": ["reportes"],
    },
    RolEnum.CONSULTOR_SENIOR: {
        "permissions": ["dashboard.view", "proyectos.manage", "boveda.manage", "tickets.manage"],
        "views": ["dashboard", "proyectos", "boveda", "taller", "perfil"],
        "tools": ["reportes", "credenciales"],
    },
}


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, str)] if isinstance(data, list) else []


def dumps_json_list(items: list[str] | None) -> str | None:
    if items is None:
        return None
    cleaned = sorted({item.strip() for item in items if item and item.strip()})
    return json.dumps(cleaned)


def get_effective_access(user: Usuario) -> dict[str, list[str]]:
    defaults = ROLE_ACCESS.get(user.rol, {"permissions": [], "views": [], "tools": []})
    permissions = sorted({*defaults["permissions"], *_load_json_list(user.permisos_json)})
    views = sorted({*defaults["views"], *_load_json_list(user.vistas_json)})
    tools = sorted({*defaults["tools"], *_load_json_list(user.herramientas_json)})
    return {"permissions": permissions, "views": views, "tools": tools}


def has_access_item(items: list[str], value: str) -> bool:
    return "*" in items or value in items