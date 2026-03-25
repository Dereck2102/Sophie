from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_superadmin
from app.core.platform_catalog import get_plan_by_tier
from app.core.database import get_db
from app.core.security import hash_one_time_secret
from app.infrastructure.models.cliente import Cliente, Empresa, EstadoClienteEnum
from app.infrastructure.models.subscriptions import (
    BillingCycleEnum,
    EmpresaSubscription,
    PlanTierEnum,
    PaymentStatusEnum,
    PaymentTransaction,
    SubscriptionStatusEnum,
)
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.platform import (
    GlobalCompanyOut,
    GlobalCompanyUpdateIn,
    GlobalCompanyUserOut,
    GlobalDashboardSummaryOut,
    GlobalPlanCountOut,
    GlobalUserActivationIn,
    GlobalUserPasswordResetOut,
)

router = APIRouter(prefix="/global", tags=["Global Layer"])


def _parse_features_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return sorted({str(item).strip() for item in data if str(item).strip()})


def _default_plan_features(plan: PlanTierEnum) -> list[str]:
    if plan == PlanTierEnum.CUSTOM:
        return []
    try:
        return list(get_plan_by_tier(plan).modules)
    except KeyError:
        return []


def _fixed_role_for_enterprise(rol: str) -> str:
    if rol == "superadmin":
        return "superadmin"
    return "admin"


@router.get("/dashboard/summary", response_model=GlobalDashboardSummaryOut)
async def get_global_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalDashboardSummaryOut:
    _ = current_user

    total_companies_result = await db.execute(select(func.count(Empresa.id_cliente)))
    total_companies = int(total_companies_result.scalar() or 0)

    active_companies_result = await db.execute(
        select(func.count(Empresa.id_cliente))
        .select_from(Empresa)
        .join(Cliente, Cliente.id_cliente == Empresa.id_cliente)
        .where(Cliente.estado == EstadoClienteEnum.ACTIVO)
    )
    active_companies = int(active_companies_result.scalar() or 0)

    registered_users_result = await db.execute(select(func.count(Usuario.id_usuario)))
    registered_users = int(registered_users_result.scalar() or 0)

    subs_result = await db.execute(select(EmpresaSubscription))
    subscriptions = list(subs_result.scalars().all())

    active_subscriptions = sum(1 for sub in subscriptions if sub.status == SubscriptionStatusEnum.ACTIVE)
    pending_subscriptions = sum(1 for sub in subscriptions if sub.status == SubscriptionStatusEnum.PENDING)

    mrr = Decimal("0")
    plan_counter: dict[str, int] = {}
    for sub in subscriptions:
        plan_key = sub.plan_tier.value
        plan_counter[plan_key] = plan_counter.get(plan_key, 0) + 1
        if sub.status != SubscriptionStatusEnum.ACTIVE:
            continue
        amount = Decimal(str(sub.price_usd or 0))
        if sub.billing_cycle == BillingCycleEnum.YEARLY:
            mrr += (amount / Decimal("12"))
        else:
            mrr += amount

    paid_transactions_result = await db.execute(
        select(func.count(PaymentTransaction.id_pago)).where(
            PaymentTransaction.status == PaymentStatusEnum.PAID
        )
    )
    paid_transactions = int(paid_transactions_result.scalar() or 0)

    return GlobalDashboardSummaryOut(
        total_companies=total_companies,
        active_companies=active_companies,
        suspended_or_inactive_companies=max(total_companies - active_companies, 0),
        registered_users=registered_users,
        active_subscriptions=active_subscriptions,
        pending_subscriptions=pending_subscriptions,
        paid_transactions=paid_transactions,
        mrr_usd=mrr.quantize(Decimal("0.01")),
        plan_breakdown=[
            GlobalPlanCountOut(tier=tier, companies=companies)
            for tier, companies in sorted(plan_counter.items(), key=lambda item: item[0])
        ],
    )


@router.get("/companies", response_model=list[GlobalCompanyOut])
async def list_global_companies(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
    limit: int = Query(300, ge=1, le=1000),
) -> list[GlobalCompanyOut]:
    _ = current_user
    empresas_result = await db.execute(select(Empresa).order_by(Empresa.razon_social.asc()).limit(limit))
    empresas = list(empresas_result.scalars().all())
    if not empresas:
        return []

    ids = [empresa.id_cliente for empresa in empresas]
    clientes_result = await db.execute(select(Cliente).where(Cliente.id_cliente.in_(ids)))
    cliente_map = {cliente.id_cliente: cliente for cliente in clientes_result.scalars().all()}
    subs_result = await db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa.in_(ids)))
    sub_map = {sub.id_empresa: sub for sub in subs_result.scalars().all()}

    output: list[GlobalCompanyOut] = []
    for empresa in empresas:
        cliente = cliente_map.get(empresa.id_cliente)
        sub = sub_map.get(empresa.id_cliente)
        if sub:
            modules = _parse_features_json(sub.features_json) or _default_plan_features(sub.plan_tier)
            output.append(
                GlobalCompanyOut(
                    id_empresa=empresa.id_cliente,
                    nombre=empresa.razon_social,
                    branding_nombre=empresa.branding_nombre,
                    branding_logo_url=empresa.branding_logo_url,
                    ruc=empresa.ruc,
                    estado=cliente.estado if cliente else EstadoClienteEnum.ACTIVO,
                    plan_tier=sub.plan_tier,
                    billing_cycle=sub.billing_cycle,
                    subscription_status=sub.status,
                    modules_enabled=modules,
                    fecha_inicio=sub.created_at,
                    price_usd=Decimal(str(sub.price_usd or 0)),
                    currency=sub.currency or "USD",
                )
            )
            continue

        output.append(
            GlobalCompanyOut(
                id_empresa=empresa.id_cliente,
                nombre=empresa.razon_social,
                branding_nombre=empresa.branding_nombre,
                branding_logo_url=empresa.branding_logo_url,
                ruc=empresa.ruc,
                estado=cliente.estado if cliente else EstadoClienteEnum.ACTIVO,
                plan_tier=PlanTierEnum.STARTER,
                billing_cycle=BillingCycleEnum.MONTHLY,
                subscription_status=SubscriptionStatusEnum.PENDING,
                modules_enabled=_default_plan_features(PlanTierEnum.STARTER),
                fecha_inicio=cliente.fecha_registro if cliente else datetime.now(timezone.utc),
                price_usd=Decimal("29.00"),
                currency="USD",
            )
        )
    return output


@router.patch("/companies/{id_empresa}", response_model=GlobalCompanyOut)
async def update_global_company(
    id_empresa: int,
    body: GlobalCompanyUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalCompanyOut:
    _ = current_user
    empresa_result = await db.execute(select(Empresa).where(Empresa.id_cliente == id_empresa))
    empresa = empresa_result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if body.nombre is not None:
        empresa.razon_social = body.nombre
    if body.branding_nombre is not None:
        empresa.branding_nombre = body.branding_nombre
    if body.branding_logo_url is not None:
        empresa.branding_logo_url = body.branding_logo_url
    if body.ruc is not None:
        empresa.ruc = body.ruc
    if body.contacto_principal is not None:
        empresa.contacto_principal = body.contacto_principal
    if body.telefono is not None:
        empresa.telefono = body.telefono
    if body.email is not None:
        empresa.email = body.email
    if body.direccion is not None:
        empresa.direccion = body.direccion
    if body.sector is not None:
        empresa.sector = body.sector

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una empresa registrada con ese RUC")

    cliente_result = await db.execute(select(Cliente).where(Cliente.id_cliente == id_empresa))
    cliente = cliente_result.scalar_one_or_none()
    sub_result = await db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == id_empresa))
    sub = sub_result.scalar_one_or_none()

    if not sub:
        return GlobalCompanyOut(
            id_empresa=empresa.id_cliente,
            nombre=empresa.razon_social,
            branding_nombre=empresa.branding_nombre,
            branding_logo_url=empresa.branding_logo_url,
            ruc=empresa.ruc,
            estado=cliente.estado if cliente else EstadoClienteEnum.ACTIVO,
            plan_tier=PlanTierEnum.STARTER,
            billing_cycle=BillingCycleEnum.MONTHLY,
            subscription_status=SubscriptionStatusEnum.PENDING,
            modules_enabled=_default_plan_features(PlanTierEnum.STARTER),
            fecha_inicio=cliente.fecha_registro if cliente else datetime.now(timezone.utc),
            price_usd=Decimal("29.00"),
            currency="USD",
        )

    return GlobalCompanyOut(
        id_empresa=empresa.id_cliente,
        nombre=empresa.razon_social,
        branding_nombre=empresa.branding_nombre,
        branding_logo_url=empresa.branding_logo_url,
        ruc=empresa.ruc,
        estado=cliente.estado if cliente else EstadoClienteEnum.ACTIVO,
        plan_tier=sub.plan_tier,
        billing_cycle=sub.billing_cycle,
        subscription_status=sub.status,
        modules_enabled=_parse_features_json(sub.features_json) or _default_plan_features(sub.plan_tier),
        fecha_inicio=sub.created_at,
        price_usd=Decimal(str(sub.price_usd or 0)),
        currency=sub.currency or "USD",
    )


@router.post("/companies/{id_empresa}/suspend", response_model=GlobalCompanyOut)
async def suspend_company(
    id_empresa: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalCompanyOut:
    _ = current_user
    cliente_result = await db.execute(select(Cliente).where(Cliente.id_cliente == id_empresa))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    cliente.estado = EstadoClienteEnum.INACTIVO

    sub_result = await db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == id_empresa))
    sub = sub_result.scalar_one_or_none()
    if sub:
        sub.status = SubscriptionStatusEnum.PAST_DUE

    await db.flush()
    return await update_global_company(id_empresa=id_empresa, body=GlobalCompanyUpdateIn(), db=db, current_user=current_user)


@router.post("/companies/{id_empresa}/activate", response_model=GlobalCompanyOut)
async def activate_company(
    id_empresa: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalCompanyOut:
    _ = current_user
    cliente_result = await db.execute(select(Cliente).where(Cliente.id_cliente == id_empresa))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    cliente.estado = EstadoClienteEnum.ACTIVO

    sub_result = await db.execute(select(EmpresaSubscription).where(EmpresaSubscription.id_empresa == id_empresa))
    sub = sub_result.scalar_one_or_none()
    if sub and sub.status in {SubscriptionStatusEnum.PAST_DUE, SubscriptionStatusEnum.CANCELED, SubscriptionStatusEnum.PENDING}:
        sub.status = SubscriptionStatusEnum.ACTIVE

    await db.flush()
    return await update_global_company(id_empresa=id_empresa, body=GlobalCompanyUpdateIn(), db=db, current_user=current_user)


@router.delete("/companies/{id_empresa}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_company_global(
    id_empresa: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> None:
    _ = current_user
    cliente_result = await db.execute(select(Cliente).where(Cliente.id_cliente == id_empresa))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    await db.delete(cliente)
    await db.flush()


@router.get("/users", response_model=list[GlobalCompanyUserOut])
async def list_global_users(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
    limit: int = Query(500, ge=1, le=2000),
) -> list[GlobalCompanyUserOut]:
    _ = current_user
    result = await db.execute(
        select(Usuario)
        .where(
            Usuario.id_cliente.is_(None),
            Usuario.rol.in_([RolEnum.SUPERADMIN, RolEnum.ADMIN]),
        )
        .order_by(Usuario.fecha_creacion.desc())
        .limit(limit)
    )
    users = list(result.scalars().all())
    if not users:
        return []

    company_ids = sorted({user.id_cliente for user in users if user.id_cliente is not None})
    empresa_map: dict[int, str] = {}
    if company_ids:
        empresas_result = await db.execute(select(Empresa).where(Empresa.id_cliente.in_(company_ids)))
        empresa_map = {empresa.id_cliente: empresa.razon_social for empresa in empresas_result.scalars().all()}

    return [
        GlobalCompanyUserOut(
            id_usuario=user.id_usuario,
            username=user.username,
            email=user.email,
            rol=user.rol,
            rol_fijo=_fixed_role_for_enterprise(user.rol.value),
            activo=user.activo,
            id_empresa=user.id_cliente,
            empresa_nombre=empresa_map.get(user.id_cliente) if user.id_cliente is not None else None,
        )
        for user in users
    ]


@router.patch("/users/{id_usuario}/activation", response_model=GlobalCompanyUserOut)
async def set_global_user_activation(
    id_usuario: int,
    body: GlobalUserActivationIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalCompanyUserOut:
    _ = current_user
    user_result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id_cliente is not None or user.rol not in {RolEnum.SUPERADMIN, RolEnum.ADMIN}:
        raise HTTPException(status_code=403, detail="Solo se pueden gestionar cuentas maestras")
    user.activo = body.activo
    await db.flush()

    empresa_nombre = None
    if user.id_cliente is not None:
        empresa_result = await db.execute(select(Empresa).where(Empresa.id_cliente == user.id_cliente))
        empresa = empresa_result.scalar_one_or_none()
        empresa_nombre = empresa.razon_social if empresa else None

    return GlobalCompanyUserOut(
        id_usuario=user.id_usuario,
        username=user.username,
        email=user.email,
        rol=user.rol,
        rol_fijo=_fixed_role_for_enterprise(user.rol.value),
        activo=user.activo,
        id_empresa=user.id_cliente,
        empresa_nombre=empresa_nombre,
    )


@router.post("/users/{id_usuario}/force-password-reset", response_model=GlobalUserPasswordResetOut)
async def force_global_user_password_reset(
    id_usuario: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalUserPasswordResetOut:
    _ = current_user
    user_result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id_cliente is not None or user.rol not in {RolEnum.SUPERADMIN, RolEnum.ADMIN}:
        raise HTTPException(status_code=403, detail="Solo se pueden gestionar cuentas maestras")

    plain_token = secrets.token_urlsafe(24)
    user.password_reset_token_hash = hash_one_time_secret(plain_token)
    user.password_reset_expira = datetime.now(timezone.utc) + timedelta(minutes=30)
    user.password_reset_intentos = 0
    await db.flush()

    return GlobalUserPasswordResetOut(
        id_usuario=user.id_usuario,
        reset_token=plain_token,
        expires_at=user.password_reset_expira,
    )