from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_superadmin
from app.core.config import get_settings
from app.core.platform_catalog import get_plan_by_tier
from app.core.database import get_db
from app.core.security import hash_one_time_secret, hash_password
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.cliente import Cliente, ClienteB2C, Empresa, EstadoClienteEnum
from app.infrastructure.models.proyectos import Proyecto
from app.infrastructure.models.subscriptions import (
    BillingCycleEnum,
    EmpresaSubscription,
    PlanTierEnum,
    PaymentStatusEnum,
    PaymentTransaction,
    SubscriptionStatusEnum,
)
from app.infrastructure.models.tickets import (
    EstadoTicketEnum,
    IncidenciaIT,
    ReparacionTaller,
    SLA,
    Ticket,
    TipoTicketEnum,
)
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.platform import (
    GlobalCompanyOut,
    GlobalCompanyUpdateIn,
    GlobalTicketClientLookupOut,
    GlobalTicketProjectLookupOut,
    GlobalCompanyUserOut,
    GlobalDashboardSummaryOut,
    GlobalPlanCountOut,
    GlobalTicketOut,
    GlobalTicketUpdateIn,
    GlobalUserCreateIn,
    GlobalUserActivationIn,
    GlobalUserPasswordResetOut,
)
from app.schemas.tickets import TicketCreate

router = APIRouter(prefix="/global", tags=["Global Layer"])
settings = get_settings()


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
    if rol == "agente_soporte":
        return "soporte"
    return "admin"


def _assert_global_ticket_access(current_user: Usuario) -> None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return

    is_global_support = (
        current_user.rol == RolEnum.AGENTE_SOPORTE
        and bool(current_user.es_admin_global)
        and current_user.id_cliente is None
    )
    if not is_global_support:
        raise HTTPException(status_code=403, detail="Acceso global de tickets restringido")


def _next_ticket_numero(count: int) -> str:
    return f"TKT-{count + 1:06d}"


_VALID_GLOBAL_ASSIGNEE_ROLES = {
    RolEnum.EJECUTIVO,
    RolEnum.TECNICO,
    RolEnum.TECNICO_TALLER,
    RolEnum.AGENTE_SOPORTE,
    RolEnum.AGENTE_SOPORTE_L1,
    RolEnum.AGENTE_SOPORTE_L2,
    RolEnum.DESARROLLADOR,
    RolEnum.SUPERADMIN,
}


def _map_global_ticket_out(
    ticket: Ticket,
    cliente: Cliente,
    empresa: Empresa | None,
    cliente_b2c: ClienteB2C | None,
    tecnico: Usuario | None,
) -> GlobalTicketOut:
    cliente_nombre = empresa.razon_social if empresa else (cliente_b2c.nombre_completo if cliente_b2c else None)
    return GlobalTicketOut(
        id_ticket=ticket.id_ticket,
        numero=ticket.numero,
        tipo=ticket.tipo,
        estado=ticket.estado,
        prioridad=ticket.prioridad,
        titulo=ticket.titulo,
        descripcion=ticket.descripcion,
        fecha_creacion=ticket.fecha_creacion,
        id_cliente=ticket.id_cliente,
        cliente_nombre=cliente_nombre,
        id_empresa=empresa.id_cliente if empresa else cliente.tenant_id,
        empresa_nombre=empresa.razon_social if empresa else None,
        id_tecnico=ticket.id_tecnico,
        tecnico_username=tecnico.username if tecnico else None,
    )


@router.get("/tickets/lookups/clients", response_model=list[GlobalTicketClientLookupOut])
async def list_global_ticket_clients_lookup(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    limit: int = Query(300, ge=1, le=1000),
) -> list[GlobalTicketClientLookupOut]:
    _assert_global_ticket_access(current_user)

    result = await db.execute(
        select(Cliente, Empresa, ClienteB2C)
        .outerjoin(Empresa, Empresa.id_cliente == Cliente.id_cliente)
        .outerjoin(ClienteB2C, ClienteB2C.id_cliente == Cliente.id_cliente)
        .order_by(Cliente.id_cliente.desc())
        .limit(limit)
    )

    output: list[GlobalTicketClientLookupOut] = []
    for cliente, empresa, cliente_b2c in result.all():
        cliente_nombre = (
            (empresa.razon_social if empresa else None)
            or (cliente_b2c.nombre_completo if cliente_b2c else None)
            or f"Cliente #{cliente.id_cliente}"
        )
        output.append(
            GlobalTicketClientLookupOut(
                id_cliente=cliente.id_cliente,
                tipo_cliente=cliente.tipo_cliente.value,
                id_empresa=empresa.id_cliente if empresa else cliente.tenant_id,
                empresa_nombre=empresa.razon_social if empresa else None,
                cliente_nombre=cliente_nombre,
                ruc=empresa.ruc if empresa else None,
            )
        )
    return output


@router.get("/tickets/lookups/clients/{id_cliente}/projects", response_model=list[GlobalTicketProjectLookupOut])
async def list_global_ticket_client_projects_lookup(
    id_cliente: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    limit: int = Query(200, ge=1, le=1000),
) -> list[GlobalTicketProjectLookupOut]:
    _assert_global_ticket_access(current_user)

    client_result = await db.execute(select(Cliente).where(Cliente.id_cliente == id_cliente))
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cliente not found")

    projects_result = await db.execute(
        select(Proyecto)
        .where(Proyecto.id_cliente == id_cliente)
        .order_by(Proyecto.fecha_creacion.desc(), Proyecto.id_proyecto.desc())
        .limit(limit)
    )
    projects = list(projects_result.scalars().all())
    return [
        GlobalTicketProjectLookupOut(
            id_proyecto=project.id_proyecto,
            id_cliente=project.id_cliente,
            nombre=project.nombre,
        )
        for project in projects
    ]


@router.get("/tickets", response_model=list[GlobalTicketOut])
async def list_global_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    estado: EstadoTicketEnum | None = Query(None),
    tipo: TipoTicketEnum | None = Query(None),
    id_empresa: int | None = Query(None, ge=1),
    id_tecnico: int | None = Query(None, ge=1),
) -> list[GlobalTicketOut]:
    _assert_global_ticket_access(current_user)

    query = (
        select(Ticket, Cliente, Empresa, ClienteB2C, Usuario)
        .join(Cliente, Cliente.id_cliente == Ticket.id_cliente)
        .outerjoin(Empresa, Empresa.id_cliente == Cliente.id_cliente)
        .outerjoin(ClienteB2C, ClienteB2C.id_cliente == Cliente.id_cliente)
        .outerjoin(Usuario, Usuario.id_usuario == Ticket.id_tecnico)
        .order_by(Ticket.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
    )

    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if tipo is not None:
        query = query.where(Ticket.tipo == tipo)
    if id_tecnico is not None:
        query = query.where(Ticket.id_tecnico == id_tecnico)
    if id_empresa is not None:
        query = query.where(or_(Empresa.id_cliente == id_empresa, Cliente.tenant_id == id_empresa))

    result = await db.execute(query)
    rows = result.all()
    return [_map_global_ticket_out(ticket, cliente, empresa, cliente_b2c, tecnico) for ticket, cliente, empresa, cliente_b2c, tecnico in rows]


@router.post("/tickets", response_model=GlobalTicketOut, status_code=status.HTTP_201_CREATED)
async def create_global_ticket(
    body: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> GlobalTicketOut:
    _assert_global_ticket_access(current_user)

    client_result = await db.execute(select(Cliente).where(Cliente.id_cliente == body.id_cliente))
    cliente = client_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")

    tecnico: Usuario | None = None
    if body.id_tecnico is not None:
        user_result = await db.execute(select(Usuario).where(Usuario.id_usuario == body.id_tecnico))
        tecnico = user_result.scalar_one_or_none()
        if not tecnico or tecnico.rol not in _VALID_GLOBAL_ASSIGNEE_ROLES:
            raise HTTPException(status_code=400, detail="Solo se pueden asignar técnicos o encargados válidos")

    if body.id_proyecto is not None:
        proyecto_result = await db.execute(select(Proyecto).where(Proyecto.id_proyecto == body.id_proyecto))
        proyecto = proyecto_result.scalar_one_or_none()
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto not found")
        if proyecto.id_cliente != body.id_cliente:
            raise HTTPException(status_code=400, detail="El proyecto seleccionado no pertenece al cliente del ticket")

    count_result = await db.execute(select(func.coalesce(func.max(Ticket.id_ticket), 0)))
    count = int(count_result.scalar_one() or 0)
    numero = _next_ticket_numero(count)

    ticket_data = body.model_dump(
        exclude={
            "equipo_descripcion",
            "marca_equipo",
            "modelo_equipo",
            "numero_serie_equipo",
            "accesorios_recibidos",
            "email_cliente",
        }
    )
    ticket = Ticket(numero=numero, **ticket_data)
    db.add(ticket)
    await db.flush()

    if body.tipo == TipoTicketEnum.REPARACION:
        token = secrets.token_urlsafe(32)
        db.add(
            ReparacionTaller(
                id_ticket=ticket.id_ticket,
                equipo_descripcion=body.equipo_descripcion,
                marca_equipo=body.marca_equipo,
                modelo_equipo=body.modelo_equipo,
                numero_serie_equipo=body.numero_serie_equipo,
                accesorios_recibidos=body.accesorios_recibidos,
                email_cliente=body.email_cliente,
                token_seguimiento=token,
            )
        )
    else:
        sla_result = await db.execute(select(SLA).where(SLA.id_empresa == body.id_cliente).limit(1))
        sla = sla_result.scalar_one_or_none()
        db.add(
            IncidenciaIT(
                id_ticket=ticket.id_ticket,
                id_sla=sla.id_sla if sla else None,
            )
        )

    db.add(
        EventoCliente(
            id_cliente=body.id_cliente,
            tipo_evento="TICKET",
            descripcion=f"Ticket {numero} creado desde panel maestro.",
        )
    )
    await db.flush()

    empresa_result = await db.execute(select(Empresa).where(Empresa.id_cliente == body.id_cliente))
    empresa = empresa_result.scalar_one_or_none()
    b2c_result = await db.execute(select(ClienteB2C).where(ClienteB2C.id_cliente == body.id_cliente))
    cliente_b2c = b2c_result.scalar_one_or_none()
    return _map_global_ticket_out(ticket, cliente, empresa, cliente_b2c, tecnico)


@router.patch("/tickets/{id_ticket}", response_model=GlobalTicketOut)
async def update_global_ticket(
    id_ticket: int,
    body: GlobalTicketUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> GlobalTicketOut:
    _assert_global_ticket_access(current_user)

    if body.estado is None and body.id_tecnico is None:
        raise HTTPException(status_code=400, detail="Debes enviar estado o id_tecnico")

    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    tecnico: Usuario | None = None
    if body.id_tecnico is not None:
        tecnico_result = await db.execute(select(Usuario).where(Usuario.id_usuario == body.id_tecnico))
        tecnico = tecnico_result.scalar_one_or_none()
        if not tecnico or tecnico.rol not in _VALID_GLOBAL_ASSIGNEE_ROLES:
            raise HTTPException(status_code=400, detail="Solo se pueden asignar técnicos o encargados válidos")
        ticket.id_tecnico = body.id_tecnico

    if body.estado is not None:
        ticket.estado = body.estado
        if body.estado in {EstadoTicketEnum.RESUELTO, EstadoTicketEnum.CERRADO}:
            ticket.fecha_cierre = datetime.now(timezone.utc)

    await db.flush()

    row_result = await db.execute(
        select(Ticket, Cliente, Empresa, ClienteB2C, Usuario)
        .join(Cliente, Cliente.id_cliente == Ticket.id_cliente)
        .outerjoin(Empresa, Empresa.id_cliente == Cliente.id_cliente)
        .outerjoin(ClienteB2C, ClienteB2C.id_cliente == Cliente.id_cliente)
        .outerjoin(Usuario, Usuario.id_usuario == Ticket.id_tecnico)
        .where(Ticket.id_ticket == id_ticket)
    )
    row = row_result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _map_global_ticket_out(*row)


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
            Usuario.rol.in_([RolEnum.SUPERADMIN, RolEnum.ADMIN, RolEnum.AGENTE_SOPORTE]),
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


@router.post("/users", response_model=GlobalCompanyUserOut, status_code=status.HTTP_201_CREATED)
async def create_global_user(
    body: GlobalUserCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> GlobalCompanyUserOut:
    _ = current_user

    allowed_roles = {RolEnum.SUPERADMIN, RolEnum.ADMIN, RolEnum.AGENTE_SOPORTE}
    if body.rol not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="En panel maestro solo se permiten roles superadmin, admin y agente_soporte",
        )

    owner_username = settings.OWNER_SUPERADMIN_USERNAME.strip().lower()
    if body.rol == RolEnum.SUPERADMIN and body.username.strip().lower() != owner_username:
        raise HTTPException(
            status_code=403,
            detail=f"Solo '{settings.OWNER_SUPERADMIN_USERNAME}' puede tener rol superadmin",
        )

    existing_result = await db.execute(
        select(Usuario).where(
            (Usuario.username == body.username) | (Usuario.email == body.email)
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        if existing.username == body.username:
            raise HTTPException(status_code=409, detail="Username ya existe")
        raise HTTPException(status_code=409, detail="Email ya existe")

    user = Usuario(
        id_cliente=None,
        id_empresa=None,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        rol=body.rol,
        nombre_completo=body.nombre_completo,
        tipo_suscripcion="corporativa",
        es_admin_global=True,
    )
    db.add(user)
    await db.flush()

    return GlobalCompanyUserOut(
        id_usuario=user.id_usuario,
        username=user.username,
        email=user.email,
        rol=user.rol,
        rol_fijo=_fixed_role_for_enterprise(user.rol.value),
        activo=user.activo,
        id_empresa=None,
        empresa_nombre=None,
    )


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
    if user.id_cliente is not None or user.rol not in {RolEnum.SUPERADMIN, RolEnum.ADMIN, RolEnum.AGENTE_SOPORTE}:
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
    if user.id_cliente is not None or user.rol not in {RolEnum.SUPERADMIN, RolEnum.ADMIN, RolEnum.AGENTE_SOPORTE}:
        raise HTTPException(status_code=403, detail="Solo se pueden gestionar cuentas maestras")

    if user.rol == RolEnum.SUPERADMIN and user.username.lower() == settings.OWNER_SUPERADMIN_USERNAME.strip().lower():
        raise HTTPException(status_code=403, detail="No se puede forzar reset del superadmin propietario")

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


@router.delete("/users/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_global_user(
    id_usuario: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> None:
    if current_user.id_usuario == id_usuario:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")

    user_result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.id_cliente is not None or user.rol not in {RolEnum.SUPERADMIN, RolEnum.ADMIN, RolEnum.AGENTE_SOPORTE}:
        raise HTTPException(status_code=403, detail="Solo se pueden gestionar cuentas maestras")

    if user.rol == RolEnum.SUPERADMIN and user.username.lower() == settings.OWNER_SUPERADMIN_USERNAME.strip().lower():
        raise HTTPException(status_code=403, detail="No se puede eliminar el superadmin propietario")

    await db.delete(user)
    await db.flush()