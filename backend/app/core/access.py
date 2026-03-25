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
        "permissions": ["*"],
        "views": [
            "auditoria", "empresas", "caja_chica", "compras", "configuracion",
            "dashboard", "inventario", "perfil", "proyectos",
            "taller", "usuarios", "ventas",
        ],
        "tools": ["*"],
    },
    RolEnum.AGENTE_SOPORTE: {
        "permissions": [
            "dashboard.view", "clientes.read", "tickets.manage", "inventario.read",
        ],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.VENTAS: {
        "permissions": [
            "dashboard.view", "clientes.manage", "ventas.manage", "reportes.view",
        ],
        "views": ["dashboard", "perfil", "ventas"],
        "tools": ["reportes", "exportaciones", "calculadora_margen"],
    },
    RolEnum.CONTABLE: {
        "permissions": [
            "dashboard.view", "compras.manage", "reportes.view", "ventas.manage",
        ],
        "views": ["dashboard", "perfil", "caja_chica", "compras", "ventas"],
        "tools": [
            "control_caja_chica", "proyecciones_financieras", "simulador_iva", "reportes",
        ],
    },
    RolEnum.RRHH: {
        "permissions": [
            "dashboard.view", "usuarios.manage", "reportes.view",
        ],
        "views": ["dashboard", "perfil", "usuarios"],
        "tools": ["reportes"],
    },
    RolEnum.BODEGA: {
        "permissions": [
            "dashboard.view", "inventario.read", "compras.manage", "reportes.view",
        ],
        "views": ["dashboard", "perfil", "inventario", "compras"],
        "tools": ["scanner_qr", "reportes"],
    },

    # Legacy roles mapped to closest new role behavior.
    RolEnum.JEFE_TECNOLOGIAS: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.JEFE_TALLER: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.JEFE_ADMINISTRATIVO: {
        "permissions": ["dashboard.view", "compras.manage", "reportes.view", "ventas.manage"],
        "views": ["dashboard", "perfil", "caja_chica", "compras", "ventas"],
        "tools": ["control_caja_chica", "proyecciones_financieras", "simulador_iva", "reportes"],
    },
    RolEnum.JEFE_CONTABLE: {
        "permissions": ["dashboard.view", "compras.manage", "reportes.view", "ventas.manage"],
        "views": ["dashboard", "perfil", "caja_chica", "compras", "ventas"],
        "tools": ["control_caja_chica", "proyecciones_financieras", "simulador_iva", "reportes"],
    },
    RolEnum.EJECUTIVO: {
        "permissions": ["dashboard.view", "clientes.manage", "ventas.manage", "reportes.view"],
        "views": ["dashboard", "perfil", "ventas"],
        "tools": ["reportes", "exportaciones", "calculadora_margen"],
    },
    RolEnum.ADMINISTRATIVO_CONTABLE: {
        "permissions": ["dashboard.view", "compras.manage", "reportes.view", "ventas.manage"],
        "views": ["dashboard", "perfil", "caja_chica", "compras", "ventas"],
        "tools": ["control_caja_chica", "proyecciones_financieras", "simulador_iva", "reportes"],
    },
    RolEnum.TECNICO: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.TECNICO_TALLER: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.AGENTE_SOPORTE_L1: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.AGENTE_SOPORTE_L2: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
    RolEnum.DESARROLLADOR: {
        "permissions": ["dashboard.view", "clientes.read", "tickets.manage", "inventario.read"],
        "views": ["dashboard", "perfil", "taller", "inventario"],
        "tools": ["scanner_qr", "reportes"],
    },
}

_ACCESS_VALUE_ALIASES: dict[str, str] = {
    "boveda": "empresas",
    "boveda.manage": "empresas.manage",
}


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, str)] if isinstance(data, list) else []


def _normalize_access_items(items: list[str]) -> list[str]:
    normalized = [_ACCESS_VALUE_ALIASES.get(item, item) for item in items]
    return sorted(set(normalized))


def dumps_json_list(items: list[str] | None) -> str | None:
    if items is None:
        return None
    cleaned = _normalize_access_items([item.strip() for item in items if item and item.strip()])
    return json.dumps(cleaned)


def get_effective_access(user: Usuario) -> dict[str, list[str]]:
    defaults = ROLE_ACCESS.get(user.rol, {"permissions": [], "views": [], "tools": []})

    if user.rol == RolEnum.SUPERADMIN:
        return {
            "permissions": _normalize_access_items(defaults["permissions"]),
            "views": _normalize_access_items(defaults["views"]),
            "tools": sorted(defaults["tools"]),
        }

    # If granular lists are explicitly configured (JSON field set, even to []),
    # they become authoritative. If not set (None), role defaults apply.
    permissions = _normalize_access_items(_load_json_list(user.permisos_json)) if user.permisos_json is not None else _normalize_access_items(defaults["permissions"])
    views = _normalize_access_items(_load_json_list(user.vistas_json)) if user.vistas_json is not None else _normalize_access_items(defaults["views"])
    tools = sorted(_load_json_list(user.herramientas_json)) if user.herramientas_json is not None else sorted(defaults["tools"])
    return {"permissions": permissions, "views": views, "tools": tools}


def has_access_item(items: list[str], value: str) -> bool:
    return "*" in items or value in items


def get_role_profiles_payload() -> dict[str, dict[str, list[str]]]:
    payload: dict[str, dict[str, list[str]]] = {}
    for role, access in ROLE_ACCESS.items():
        payload[role.value] = {
            "permisos": _normalize_access_items(list(access.get("permissions", []))),
            "vistas": _normalize_access_items(list(access.get("views", []))),
            "herramientas": sorted(list(access.get("tools", []))),
        }
    return payload