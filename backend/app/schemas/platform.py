from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime

from pydantic import BaseModel

from app.infrastructure.models.cliente import EstadoClienteEnum
from app.infrastructure.models.subscriptions import BillingCycleEnum, PlanTierEnum, SubscriptionStatusEnum
from app.infrastructure.models.tickets import EstadoTicketEnum, PrioridadEnum, TipoTicketEnum
from app.infrastructure.models.usuario import RolEnum


class PlatformLayerOut(BaseModel):
    key: str
    name: str
    description: str


class PlatformModuleOut(BaseModel):
    key: str
    name: str
    layer: str
    description: str


class PublicPlanOut(BaseModel):
    key: str
    name: str
    tier: str
    description: str
    monthly_price_usd: Decimal | None
    yearly_price_usd: Decimal | None
    modules: list[str]


class PublicLandingOut(BaseModel):
    platform_name: str
    platform_version: str
    layers: list[PlatformLayerOut]
    plans: list[PublicPlanOut]


class GlobalPlanCountOut(BaseModel):
    tier: str
    companies: int


class GlobalDashboardSummaryOut(BaseModel):
    total_companies: int
    active_companies: int
    suspended_or_inactive_companies: int
    registered_users: int
    active_subscriptions: int
    pending_subscriptions: int
    paid_transactions: int
    mrr_usd: Decimal
    plan_breakdown: list[GlobalPlanCountOut]
    system_status: str = "ok"


class GlobalCompanyOut(BaseModel):
    id_empresa: int
    nombre: str
    branding_nombre: str | None = None
    branding_logo_url: str | None = None
    ruc: str
    estado: EstadoClienteEnum
    plan_tier: PlanTierEnum
    billing_cycle: BillingCycleEnum
    subscription_status: SubscriptionStatusEnum
    modules_enabled: list[str]
    fecha_inicio: date | datetime
    price_usd: Decimal
    currency: str


class GlobalCompanyUpdateIn(BaseModel):
    nombre: str | None = None
    branding_nombre: str | None = None
    branding_logo_url: str | None = None
    ruc: str | None = None
    contacto_principal: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    sector: str | None = None


class GlobalCompanyUserOut(BaseModel):
    id_usuario: int
    username: str
    email: str
    rol: RolEnum
    rol_fijo: str
    activo: bool
    id_empresa: int | None
    empresa_nombre: str | None


class GlobalUserCreateIn(BaseModel):
    username: str
    email: str
    password: str
    nombre_completo: str | None = None
    rol: RolEnum


class GlobalUserActivationIn(BaseModel):
    activo: bool


class GlobalUserPasswordResetOut(BaseModel):
    id_usuario: int
    reset_token: str
    expires_at: datetime


class GlobalTicketOut(BaseModel):
    id_ticket: int
    numero: str
    tipo: TipoTicketEnum
    estado: EstadoTicketEnum
    prioridad: PrioridadEnum
    titulo: str
    descripcion: str | None = None
    fecha_creacion: datetime
    id_cliente: int
    cliente_nombre: str | None = None
    id_empresa: int | None = None
    empresa_nombre: str | None = None
    id_tecnico: int | None = None
    tecnico_username: str | None = None


class GlobalTicketUpdateIn(BaseModel):
    estado: EstadoTicketEnum | None = None
    id_tecnico: int | None = None


class GlobalTicketClientLookupOut(BaseModel):
    id_cliente: int
    tipo_cliente: str
    id_empresa: int | None = None
    empresa_nombre: str | None = None
    cliente_nombre: str
    ruc: str | None = None


class GlobalTicketProjectLookupOut(BaseModel):
    id_proyecto: int
    id_cliente: int
    nombre: str