from __future__ import annotations

import json

from app.infrastructure.models.usuario import RolEnum, Usuario

ROLE_ACCESS: dict[RolEnum, dict[str, list[str]]] = {
    # ─── Nivel 0: Superadministrador ───────────────────────────────────────────
    RolEnum.SUPERADMIN: {
        "permissions": ["*"],
        "views": ["*"],
        "tools": ["*"],
    },
    # ─── Nivel 1: Admin general ──────────────────────────────────────────────
    RolEnum.ADMIN: {
        # Acceso completo excepto auditoría avanzada; puede gestionar usuarios no-superadmin
        "permissions": ["*"],
        "views": [
            "auditoria", "boveda", "caja_chica", "compras", "configuracion",
            "crm", "dashboard", "inventario", "perfil", "proyectos",
            "taller", "usuarios", "ventas",
        ],
        "tools": ["*"],
    },
    # ─── Nivel 2: Jefaturas de departamento ──────────────────────────────────
    RolEnum.JEFE_TECNOLOGIAS: {
        # Supervisa proyectos, taller, bóveda y equipo técnico
        "permissions": [
            "dashboard.view", "proyectos.manage", "tickets.manage",
            "clientes.read", "inventario.read", "boveda.manage", "reportes.view",
        ],
        "views": ["boveda", "crm", "dashboard", "perfil", "proyectos", "taller"],
        "tools": ["calculo_horas_tecnicas", "exportaciones", "reportes", "scanner_qr"],
    },
    RolEnum.JEFE_TALLER: {
        # Supervisa operaciones del taller, todos los tickets y proyectos
        "permissions": [
            "dashboard.view", "tickets.manage", "proyectos.read",
            "clientes.read", "inventario.read", "reportes.view",
        ],
        "views": ["crm", "dashboard", "inventario", "perfil", "proyectos", "taller"],
        "tools": ["calculo_horas_tecnicas", "exportaciones", "reportes", "scanner_qr"],
    },
    RolEnum.JEFE_ADMINISTRATIVO: {
        # Gestión integral del área administrativa
        "permissions": [
            "dashboard.view", "clientes.manage", "ventas.manage", "compras.manage",
            "inventario.read", "reportes.view",
        ],
        "views": ["caja_chica", "compras", "crm", "dashboard", "perfil", "proyectos", "ventas"],
        "tools": [
            "calculadora_margen", "control_caja_chica", "costeo_cotizaciones",
            "exportaciones", "proyecciones_financieras", "reportes",
        ],
    },
    RolEnum.JEFE_CONTABLE: {
        # Gestión contable, financiera y auditoría interna
        "permissions": [
            "dashboard.view", "ventas.manage", "compras.manage", "reportes.view",
        ],
        "views": ["auditoria", "caja_chica", "compras", "dashboard", "perfil", "ventas"],
        "tools": [
            "calculadora_margen", "control_caja_chica", "costeo_cotizaciones",
            "exportaciones", "proyecciones_financieras", "reportes",
            "simulador_descuentos", "simulador_iva",
        ],
    },
    # ─── Nivel 3: Roles de operación transversal ─────────────────────────────
    RolEnum.EJECUTIVO: {
        # Supervisión ejecutiva: operaciones, proyectos y CRM
        "permissions": [
            "dashboard.view", "clientes.manage", "ventas.manage",
            "proyectos.manage", "tickets.manage", "inventario.read",
            "boveda.manage", "reportes.view",
        ],
        "views": ["boveda", "crm", "dashboard", "inventario", "perfil", "proyectos", "taller", "ventas"],
        "tools": ["exportaciones", "reportes"],
    },
    RolEnum.ADMINISTRATIVO_CONTABLE: {
        # Gestión financiera, compras y contabilidad operativa
        "permissions": [
            "dashboard.view", "compras.manage", "ventas.manage",
            "clientes.manage", "inventario.read", "reportes.view",
        ],
        "views": ["caja_chica", "compras", "crm", "dashboard", "inventario", "perfil", "ventas"],
        "tools": [
            "calculadora_margen", "control_caja_chica", "costeo_cotizaciones",
            "exportaciones", "proyecciones_financieras", "reportes",
            "simulador_descuentos", "simulador_iva",
        ],
    },
    # ─── Nivel 4: Personal técnico y de soporte ───────────────────────────────
    RolEnum.TECNICO: {
        # Técnico general: solo sus propios tickets de taller
        "permissions": ["inventario.read", "tickets.manage"],
        "views": ["perfil", "taller"],
        "tools": ["calculo_horas_tecnicas", "scanner_qr"],
    },
    RolEnum.TECNICO_TALLER: {
        # Técnico especialista de taller: solo sus propios tickets
        "permissions": ["inventario.read", "tickets.manage"],
        "views": ["perfil", "taller"],
        "tools": ["calculo_horas_tecnicas", "scanner_qr"],
    },
    RolEnum.AGENTE_SOPORTE_L1: {
        # Soporte nivel 1: atiende tickets básicos y consulta CRM
        "permissions": ["clientes.read", "tickets.manage"],
        "views": ["crm", "perfil", "taller"],
        "tools": ["scanner_qr"],
    },
    RolEnum.AGENTE_SOPORTE_L2: {
        # Soporte nivel 2: atiende tickets complejos, puede ver proyectos
        "permissions": ["clientes.read", "inventario.read", "proyectos.read", "tickets.manage"],
        "views": ["crm", "perfil", "proyectos", "taller"],
        "tools": ["calculo_horas_tecnicas", "reportes", "scanner_qr"],
    },
    RolEnum.DESARROLLADOR: {
        # Desarrollador: proyectos, taller, bóveda de credenciales
        "permissions": ["inventario.read", "proyectos.manage", "tickets.manage"],
        "views": ["boveda", "dashboard", "perfil", "proyectos", "taller"],
        "tools": ["calculo_horas_tecnicas", "reportes", "scanner_qr"],
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

    if user.rol == RolEnum.SUPERADMIN:
        return {
            "permissions": sorted(defaults["permissions"]),
            "views": sorted(defaults["views"]),
            "tools": sorted(defaults["tools"]),
        }

    # If granular lists are explicitly configured (JSON field set, even to []),
    # they become authoritative. If not set (None), role defaults apply.
    permissions = sorted(_load_json_list(user.permisos_json)) if user.permisos_json is not None else sorted(defaults["permissions"])
    views = sorted(_load_json_list(user.vistas_json)) if user.vistas_json is not None else sorted(defaults["views"])
    tools = sorted(_load_json_list(user.herramientas_json)) if user.herramientas_json is not None else sorted(defaults["tools"])
    return {"permissions": permissions, "views": views, "tools": tools}


def has_access_item(items: list[str], value: str) -> bool:
    return "*" in items or value in items