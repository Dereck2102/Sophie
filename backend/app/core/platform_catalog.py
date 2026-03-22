from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.models.subscriptions import PlanTierEnum


@dataclass(frozen=True)
class LayerDefinition:
    key: str
    name: str
    description: str


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    name: str
    layer: str
    description: str


@dataclass(frozen=True)
class PlanDefinition:
    key: str
    name: str
    tier: PlanTierEnum
    description: str
    monthly_price_usd: float | None
    yearly_price_usd: float | None
    modules: list[str]


LAYERS: tuple[LayerDefinition, ...] = (
    LayerDefinition(
        key="public",
        name="Capa Pública",
        description="Landing, presentación de planes y onboarding/autogestión inicial.",
    ),
    LayerDefinition(
        key="global",
        name="Capa Global",
        description="Backoffice de SOPHIE exclusivo para superadmin.",
    ),
    LayerDefinition(
        key="enterprise",
        name="Capa de Empresa",
        description="ERP multiempresa con acceso por plan y permisos de usuario.",
    ),
)


MODULES: tuple[ModuleDefinition, ...] = (
    ModuleDefinition("P1", "Presentación y Planes", "public", "Landing + comparación de planes"),
    ModuleDefinition("P2", "Registro y Onboarding", "public", "Alta de usuario/empresa y activación"),
    ModuleDefinition("G1", "Dashboard Global", "global", "KPIs globales de plataforma"),
    ModuleDefinition("G2", "Gestión de Empresas", "global", "Administración de empresas cliente"),
    ModuleDefinition("G3", "Planes y Facturación", "global", "Catálogo de planes y cobros"),
    ModuleDefinition("G4", "Configuración Global", "global", "Parámetros e integraciones globales"),
    ModuleDefinition("G5", "Auditoría Global", "global", "Log de eventos y acciones superadmin"),
    ModuleDefinition("E1", "Configuración de Empresa", "enterprise", "Perfil, roles, usuarios y preferencias"),
    ModuleDefinition("E2", "Transversales", "enterprise", "Dashboard, notificaciones y auditoría interna"),
    ModuleDefinition("E3", "Gestión Financiera", "enterprise", "Caja, ingresos, egresos y declaraciones"),
    ModuleDefinition("E4", "Ventas y CRM", "enterprise", "Clientes, cotizaciones y ventas"),
    ModuleDefinition("E5", "Compras e Inventario", "enterprise", "Compras, catálogo y kardex"),
    ModuleDefinition("E6", "Proyectos", "enterprise", "Seguimiento y operación por proyectos"),
    ModuleDefinition("E7", "Operaciones", "enterprise", "Flujo operativo unificado"),
    ModuleDefinition("E8", "Tickets", "enterprise", "Servicio al cliente y soporte"),
)


PLAN_DEFINITIONS: tuple[PlanDefinition, ...] = (
    PlanDefinition(
        key="basic",
        name="Basic",
        tier=PlanTierEnum.STARTER,
        description="Base operativa para empresas pequeñas.",
        monthly_price_usd=29.0,
        yearly_price_usd=290.0,
        modules=["E1", "E2", "E3", "E4", "E5", "E8"],
    ),
    PlanDefinition(
        key="plus",
        name="Plus",
        tier=PlanTierEnum.PRO,
        description="Plan intermedio con mayor cobertura operativa.",
        monthly_price_usd=79.0,
        yearly_price_usd=790.0,
        modules=["E1", "E2", "E3", "E4", "E5", "E6", "E8"],
    ),
    PlanDefinition(
        key="enterprise",
        name="Enterprise",
        tier=PlanTierEnum.ENTERPRISE,
        description="Plan completo con trazabilidad y operación avanzada.",
        monthly_price_usd=149.0,
        yearly_price_usd=1490.0,
        modules=["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
    ),
    PlanDefinition(
        key="custom",
        name="Personalizado",
        tier=PlanTierEnum.CUSTOM,
        description="Paquete por requerimientos y módulos asignados por superadmin.",
        monthly_price_usd=None,
        yearly_price_usd=None,
        modules=[],
    ),
)


def get_plan_by_tier(tier: PlanTierEnum) -> PlanDefinition:
    for plan in PLAN_DEFINITIONS:
        if plan.tier == tier:
            return plan
    raise KeyError(f"Plan no definido para tier={tier}")


def get_modules_by_layer(layer: str) -> list[ModuleDefinition]:
    return [module for module in MODULES if module.layer == layer]