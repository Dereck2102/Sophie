from __future__ import annotations

import json

from app.infrastructure.models.usuario import RolEnum, Usuario

ROLE_ACCESS: dict[RolEnum, dict[str, list[str]]] = {
    RolEnum.SUPERADMIN: {
        "permissions": ["*"],  # Acceso total, incluyendo admin y configuración
        "views": ["*"],
        "tools": ["*"],
    },
    RolEnum.EJECUTIVO: {
        # Gestión de operaciones, supervisión de proyectos y equipos
        "permissions": [
            "dashboard.view",
            "clientes.manage",
            "ventas.manage",
            "proyectos.manage",
            "tickets.manage",
            "inventario.read",
            "reportes.view",
        ],
        "views": [
            "dashboard",
            "crm",
            "ventas",
            "proyectos",
            "taller",
            "inventario",
            "perfil",
        ],
        "tools": ["reportes", "exportaciones"],
    },
    RolEnum.ADMINISTRATIVO_CONTABLE: {
        # Gestión financiera, compras, contabilidad y documentación
        "permissions": [
            "dashboard.view",
            "compras.manage",
            "ventas.manage",
            "clientes.manage",
            "inventario.read",
            "reportes.view",
        ],
        "views": [
            "dashboard",
            "crm",
            "ventas",
            "compras",
            "inventario",
            "perfil",
        ],
        "tools": [
            "reportes",
            "exportaciones",
            "calculadora_margen",
            "proyecciones_financieras",
            "simulador_iva",
            "simulador_descuentos",
            "costeo_cotizaciones",
            "control_caja_chica",
        ],
    },
    RolEnum.TECNICO: {
        # Operación técnica, atención de tickets y ejecución de taller
        "permissions": [
            "dashboard.view",
            "tickets.manage",
            "proyectos.read",
            "clientes.read",
            "inventario.read",
            "reportes.view",
        ],
        "views": [
            "dashboard",
            "taller",
            "proyectos",
            "crm",
            "inventario",
            "perfil",
        ],
        "tools": ["reportes", "scanner_qr", "calculo_horas_tecnicas"],
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