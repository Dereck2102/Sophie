from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.money import money, percentage, to_decimal
from app.infrastructure.models.cliente import Cliente, EstadoClienteEnum
from app.infrastructure.models.caja_chica import MovimientoCajaChica, TipoMovimientoCajaEnum
from app.infrastructure.models.compras import EstadoOrdenEnum, OrdenCompra
from app.infrastructure.models.inventario import Inventario
from app.infrastructure.models.proyectos import EstadoProyectoEnum, Proyecto
from app.infrastructure.models.tickets import EstadoTicketEnum, Ticket
from app.infrastructure.models.usuario import Usuario
from app.infrastructure.models.ventas import Cotizacion, DetalleCotizacion, EstadoCotizacionEnum, Venta
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardCorrelationMetric,
    DashboardExpenseCategory,
    DashboardFinanceAnalytics,
    DashboardReceivableBucket,
    DashboardReceivableDueItem,
    DashboardStats,
    DashboardTopClient,
    DashboardTrendPoint,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _month_window(base: datetime, offset: int) -> tuple[datetime, datetime, str]:
    month = base.month + offset
    year = base.year
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1

    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end, start.strftime("%b %Y")


def _client_display_name(client: Cliente | None) -> str:
    if client is None:
        return "Cliente sin nombre"
    if client.empresa and client.empresa.razon_social:
        return client.empresa.razon_social
    if client.cliente_b2c and client.cliente_b2c.nombre_completo:
        return client.cliente_b2c.nombre_completo
    return f"Cliente #{client.id_cliente}"


def _month_bucket_expr(dialect_name: str, column):
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m", column)
    return func.to_char(func.date_trunc("month", column), "YYYY-MM")


def _month_key_from_bucket(bucket: str | None) -> tuple[int, int] | None:
    if not bucket:
        return None
    try:
        year_str, month_str = bucket.split("-", 1)
        return int(year_str), int(month_str)
    except (TypeError, ValueError):
        return None


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DashboardStats:
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    caja_scope = []
    if current_user.id_cliente is not None:
        caja_scope.append(MovimientoCajaChica.id_cliente == current_user.id_cliente)

    # Active clients
    clientes_result = await db.execute(
        select(func.count(Cliente.id_cliente)).where(
            Cliente.estado == EstadoClienteEnum.ACTIVO
        )
    )
    total_clientes = clientes_result.scalar_one() or 0

    # Cotizaciones this month
    cotizaciones_result = await db.execute(
        select(func.count(Cotizacion.id_cotizacion)).where(
            Cotizacion.fecha_creacion >= inicio_mes
        )
    )
    cotizaciones_mes = cotizaciones_result.scalar_one() or 0

    # Open tickets
    tickets_result = await db.execute(
        select(func.count(Ticket.id_ticket)).where(
            Ticket.estado.in_([EstadoTicketEnum.ABIERTO, EstadoTicketEnum.EN_PROGRESO])
        )
    )
    tickets_abiertos = tickets_result.scalar_one() or 0

    # Products below minimum stock
    stock_result = await db.execute(
        select(func.count(Inventario.id_producto)).where(
            Inventario.stock_actual <= Inventario.stock_minimo
        )
    )
    productos_bajo_stock = stock_result.scalar_one() or 0

    # Revenue this month (sum of totals of invoiced cotizaciones this month)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
    )
    revenue_mes = int(money(revenue_result.scalar_one() or 0))

    # Active projects
    proyectos_result = await db.execute(
        select(func.count(Proyecto.id_proyecto)).where(
            Proyecto.estado == EstadoProyectoEnum.EN_PROGRESO
        )
    )
    proyectos_activos = proyectos_result.scalar_one() or 0

    margen_result = await db.execute(
        select(
            func.coalesce(
                func.sum(DetalleCotizacion.subtotal - (DetalleCotizacion.cantidad * Inventario.costo_adquisicion)),
                0,
            )
        )
        .join(Cotizacion, Cotizacion.id_cotizacion == DetalleCotizacion.id_cotizacion)
        .join(Inventario, Inventario.id_producto == DetalleCotizacion.id_producto)
        .where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
    )
    margen_bruto_mes = money(margen_result.scalar_one() or 0)

    caja_balance_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.INGRESO, MovimientoCajaChica.monto),
                        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO, -MovimientoCajaChica.monto),
                        else_=MovimientoCajaChica.monto,
                    )
                ),
                0,
            )
        )
        .where(*caja_scope)
    )
    caja_chica_balance = money(caja_balance_result.scalar_one() or 0)

    caja_egresos_result = await db.execute(
        select(func.coalesce(func.sum(MovimientoCajaChica.monto), 0)).where(
            MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO,
            MovimientoCajaChica.fecha >= inicio_mes,
            *caja_scope,
        )
    )
    caja_chica_egresos_mes = money(caja_egresos_result.scalar_one() or 0)

    return DashboardStats(
        total_clientes=total_clientes,
        cotizaciones_mes=cotizaciones_mes,
        tickets_abiertos=tickets_abiertos,
        productos_bajo_stock=productos_bajo_stock,
        revenue_mes=revenue_mes,
        proyectos_activos=proyectos_activos,
        margen_bruto_mes=money(margen_bruto_mes),
        caja_chica_balance=money(caja_chica_balance),
        caja_chica_egresos_mes=money(caja_chica_egresos_mes),
    )


@router.get("/analytics", response_model=DashboardFinanceAnalytics)
async def get_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DashboardFinanceAnalytics:
    _ = current_user
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    caja_scope = []
    if current_user.id_cliente is not None:
        caja_scope.append(MovimientoCajaChica.id_cliente == current_user.id_cliente)

    ingresos_facturados_mes = await db.scalar(
        select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
    )

    compras_registradas_mes = await db.scalar(
        select(func.coalesce(func.sum(OrdenCompra.total), 0)).where(
            OrdenCompra.fecha_creacion >= inicio_mes,
            OrdenCompra.estado != EstadoOrdenEnum.CANCELADA,
        )
    )

    caja_totales = await db.execute(
        select(
            MovimientoCajaChica.tipo,
            func.coalesce(func.sum(MovimientoCajaChica.monto), 0),
        )
        .where(MovimientoCajaChica.fecha >= inicio_mes, *caja_scope)
        .group_by(MovimientoCajaChica.tipo)
    )
    caja_map = {tipo: money(total or 0) for tipo, total in caja_totales.all()}
    caja_ingresos_mes = caja_map.get(TipoMovimientoCajaEnum.INGRESO, 0.0)
    caja_egresos_mes = caja_map.get(TipoMovimientoCajaEnum.EGRESO, 0.0)

    cuentas_por_cobrar = await db.scalar(
        select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
            Cotizacion.estado.in_([
                EstadoCotizacionEnum.ENVIADA,
                EstadoCotizacionEnum.APROBADA,
            ])
        )
    )

    ordenes_pendientes_monto = await db.scalar(
        select(func.coalesce(func.sum(OrdenCompra.total), 0)).where(
            OrdenCompra.estado.in_([
                EstadoOrdenEnum.BORRADOR,
                EstadoOrdenEnum.ENVIADA,
                EstadoOrdenEnum.RECIBIDA_PARCIAL,
            ])
        )
    )

    margen_bruto_mes = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    DetalleCotizacion.subtotal
                    - (DetalleCotizacion.cantidad * Inventario.costo_adquisicion)
                ),
                0,
            )
        )
        .join(Cotizacion, Cotizacion.id_cotizacion == DetalleCotizacion.id_cotizacion)
        .join(Inventario, Inventario.id_producto == DetalleCotizacion.id_producto)
        .where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
    )

    caja_balance = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.INGRESO, MovimientoCajaChica.monto),
                        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO, -MovimientoCajaChica.monto),
                        else_=MovimientoCajaChica.monto,
                    )
                ),
                0,
            )
        )
        .where(*caja_scope)
    )

    flujo_neto_mes = money(
        to_decimal(ingresos_facturados_mes or 0)
        + to_decimal(caja_ingresos_mes or 0)
        - to_decimal(compras_registradas_mes or 0)
        - to_decimal(caja_egresos_mes or 0)
    )

    top_client_rows = await db.execute(
        select(
            Cotizacion.id_cliente,
            func.coalesce(func.sum(Cotizacion.total), 0).label("facturado"),
        )
        .where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
        .group_by(Cotizacion.id_cliente)
        .order_by(desc("facturado"))
        .limit(5)
    )
    top_client_data = top_client_rows.all()
    client_ids = [client_id for client_id, _ in top_client_data if client_id is not None]
    client_map: dict[int, Cliente] = {}
    if client_ids:
        clients = await db.scalars(
            select(Cliente)
            .options(selectinload(Cliente.empresa), selectinload(Cliente.cliente_b2c))
            .where(Cliente.id_cliente.in_(client_ids))
        )
        client_map = {client.id_cliente: client for client in clients.all()}

    total_top = sum((to_decimal(total or 0) for _, total in top_client_data), start=to_decimal(0))
    top_clientes = [
        DashboardTopClient(
            id_cliente=int(client_id),
            nombre=_client_display_name(client_map.get(int(client_id))),
            total_facturado=money(total or 0),
            participacion_pct=percentage(total or 0, total_top),
        )
        for client_id, total in top_client_data
        if client_id is not None
    ]

    categorias_rows = await db.execute(
        select(
            func.coalesce(MovimientoCajaChica.categoria, "Sin categoria").label("categoria"),
            func.coalesce(func.sum(MovimientoCajaChica.monto), 0).label("total"),
        )
        .where(
            MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO,
            MovimientoCajaChica.fecha >= inicio_mes,
        )
        .group_by(func.coalesce(MovimientoCajaChica.categoria, "Sin categoria"))
        .order_by(desc("total"))
        .limit(8)
    )
    egresos_por_categoria = [
        DashboardExpenseCategory(categoria=str(categoria), total=money(total or 0))
        for categoria, total in categorias_rows.all()
    ]

    receivable_rows = await db.scalars(
        select(Cotizacion)
        .options(selectinload(Cotizacion.cliente).selectinload(Cliente.empresa), selectinload(Cotizacion.cliente).selectinload(Cliente.cliente_b2c))
        .where(Cotizacion.estado.in_([EstadoCotizacionEnum.ENVIADA, EstadoCotizacionEnum.APROBADA]))
        .order_by(Cotizacion.fecha_vencimiento.asc().nullslast(), Cotizacion.fecha_creacion.asc())
    )
    receivables = receivable_rows.all()

    aging_totals = {
        "Vigente": {"total": to_decimal(0), "cantidad": 0},
        "Vencido 1-30": {"total": to_decimal(0), "cantidad": 0},
        "Vencido 31-60": {"total": to_decimal(0), "cantidad": 0},
        "Vencido 61+": {"total": to_decimal(0), "cantidad": 0},
        "Sin vencimiento": {"total": to_decimal(0), "cantidad": 0},
    }

    proximos_vencimientos: list[DashboardReceivableDueItem] = []
    for cotizacion in receivables:
        total = money(cotizacion.total or 0)
        fecha_vencimiento = cotizacion.fecha_vencimiento
        cliente_nombre = _client_display_name(cotizacion.cliente)

        if fecha_vencimiento is None:
            bucket = "Sin vencimiento"
            dias_para_vencer = None
            dias_vencido = None
        else:
            dias_delta = (fecha_vencimiento.date() - now.date()).days
            dias_para_vencer = dias_delta if dias_delta >= 0 else 0
            dias_vencido = abs(dias_delta) if dias_delta < 0 else 0
            if dias_delta >= 0:
                bucket = "Vigente"
            elif dias_delta >= -30:
                bucket = "Vencido 1-30"
            elif dias_delta >= -60:
                bucket = "Vencido 31-60"
            else:
                bucket = "Vencido 61+"

            if len(proximos_vencimientos) < 12:
                proximos_vencimientos.append(
                    DashboardReceivableDueItem(
                        id_cotizacion=cotizacion.id_cotizacion,
                        numero=cotizacion.numero,
                        id_cliente=cotizacion.id_cliente,
                        cliente_nombre=cliente_nombre,
                        estado=cotizacion.estado.value,
                        total=money(total),
                        fecha_vencimiento=fecha_vencimiento.date().isoformat(),
                        dias_para_vencer=dias_para_vencer,
                        dias_vencido=dias_vencido,
                    )
                )

        aging_totals[bucket]["total"] += to_decimal(total)
        aging_totals[bucket]["cantidad"] += 1

    cartera_aging = [
        DashboardReceivableBucket(
            bucket=bucket,
            total=money(values["total"]),
            cantidad=int(values["cantidad"]),
        )
        for bucket, values in aging_totals.items()
    ]

    trend_start, _, _ = _month_window(inicio_mes, -5)
    trend_end, _, _ = _month_window(inicio_mes, 1)
    dialect_name = db.bind.dialect.name if db.bind is not None else "sqlite"

    cot_month_bucket = _month_bucket_expr(dialect_name, Cotizacion.fecha_creacion)
    compras_month_bucket = _month_bucket_expr(dialect_name, OrdenCompra.fecha_creacion)
    caja_month_bucket = _month_bucket_expr(dialect_name, MovimientoCajaChica.fecha)

    ingresos_rows = await db.execute(
        select(
            cot_month_bucket.label("bucket"),
            func.coalesce(func.sum(Cotizacion.total), 0).label("total"),
        )
        .where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= trend_start,
            Cotizacion.fecha_creacion < trend_end,
        )
        .group_by(cot_month_bucket)
    )
    compras_rows = await db.execute(
        select(
            compras_month_bucket.label("bucket"),
            func.coalesce(func.sum(OrdenCompra.total), 0).label("total"),
        )
        .where(
            OrdenCompra.fecha_creacion >= trend_start,
            OrdenCompra.fecha_creacion < trend_end,
            OrdenCompra.estado != EstadoOrdenEnum.CANCELADA,
        )
        .group_by(compras_month_bucket)
    )
    caja_rows = await db.execute(
        select(
            caja_month_bucket.label("bucket"),
            MovimientoCajaChica.tipo,
            func.coalesce(func.sum(MovimientoCajaChica.monto), 0).label("total"),
        )
        .where(
            MovimientoCajaChica.fecha >= trend_start,
            MovimientoCajaChica.fecha < trend_end,
        )
        .group_by(caja_month_bucket, MovimientoCajaChica.tipo)
    )

    ingresos_by_month: dict[tuple[int, int], object] = {}
    compras_by_month: dict[tuple[int, int], object] = {}
    caja_ingresos_by_month: dict[tuple[int, int], object] = {}
    caja_egresos_by_month: dict[tuple[int, int], object] = {}

    for bucket, total in ingresos_rows.all():
        key = _month_key_from_bucket(bucket)
        if key is None:
            continue
        ingresos_by_month[key] = ingresos_by_month.get(key, to_decimal(0)) + to_decimal(total or 0)

    for bucket, total in compras_rows.all():
        key = _month_key_from_bucket(bucket)
        if key is None:
            continue
        compras_by_month[key] = compras_by_month.get(key, to_decimal(0)) + to_decimal(total or 0)

    for bucket, tipo, monto in caja_rows.all():
        key = _month_key_from_bucket(bucket)
        if key is None:
            continue
        if tipo == TipoMovimientoCajaEnum.INGRESO:
            caja_ingresos_by_month[key] = caja_ingresos_by_month.get(key, to_decimal(0)) + to_decimal(monto or 0)
        elif tipo == TipoMovimientoCajaEnum.EGRESO:
            caja_egresos_by_month[key] = caja_egresos_by_month.get(key, to_decimal(0)) + to_decimal(monto or 0)

    tendencia_mensual: list[DashboardTrendPoint] = []
    for offset in range(-5, 1):
        start, _, label = _month_window(inicio_mes, offset)
        key = (start.year, start.month)

        ingresos_money = money(ingresos_by_month.get(key, to_decimal(0)))
        compras_money = money(compras_by_month.get(key, to_decimal(0)))
        caja_ingresos_money = money(caja_ingresos_by_month.get(key, to_decimal(0)))
        caja_egresos_money = money(caja_egresos_by_month.get(key, to_decimal(0)))
        flujo_neto = money(
            to_decimal(ingresos_money)
            + to_decimal(caja_ingresos_money)
            - to_decimal(compras_money)
            - to_decimal(caja_egresos_money)
        )

        tendencia_mensual.append(
            DashboardTrendPoint(
                label=label,
                ingresos=ingresos_money,
                compras=compras_money,
                caja_ingresos=caja_ingresos_money,
                caja_egresos=caja_egresos_money,
                flujo_neto=flujo_neto,
            )
        )

    alertas: list[DashboardAlert] = []
    caja_balance_money = money(caja_balance or 0)
    ingresos_facturados_money = money(ingresos_facturados_mes or 0)
    cuentas_por_cobrar_money = money(cuentas_por_cobrar or 0)
    ordenes_pendientes_money = money(ordenes_pendientes_monto or 0)
    caja_ingresos_money = money(caja_ingresos_mes or 0)
    caja_egresos_money = money(caja_egresos_mes or 0)

    if caja_balance_money <= 0:
        alertas.append(
            DashboardAlert(
                severity="critical",
                title="Caja chica comprometida",
                detail="El balance de caja chica esta en cero o negativo. Conviene revisar reposiciones y egresos urgentes.",
                link="/caja-chica",
            )
        )
    if cuentas_por_cobrar_money > max(ingresos_facturados_money * 0.75, 500):
        alertas.append(
            DashboardAlert(
                severity="warning",
                title="Cobros pendientes altos",
                detail="Las cotizaciones aprobadas o enviadas ya superan un umbral prudente frente a la facturacion del mes.",
                link="/ventas",
            )
        )
    if ordenes_pendientes_money > ingresos_facturados_money:
        alertas.append(
            DashboardAlert(
                severity="warning",
                title="Compromiso de compras elevado",
                detail="El monto de ordenes pendientes es mayor que la facturacion registrada del mes.",
                link="/compras",
            )
        )
    if caja_egresos_money > max(caja_ingresos_money * 1.25, 300):
        alertas.append(
            DashboardAlert(
                severity="info",
                title="Gasto de caja acelerado",
                detail="Los egresos de caja chica estan creciendo mas rapido que los ingresos registrados.",
                link="/caja-chica",
            )
        )
    if flujo_neto_mes < 0:
        alertas.append(
            DashboardAlert(
                severity="critical",
                title="Flujo operativo negativo",
                detail="La combinacion de ventas facturadas, compras y caja chica deja un flujo mensual negativo.",
                link="/dashboard",
            )
        )

    tickets_abiertos = await db.scalar(
        select(func.count(Ticket.id_ticket)).where(
            Ticket.estado.in_([EstadoTicketEnum.ABIERTO, EstadoTicketEnum.EN_PROGRESO])
        )
    )
    cotizaciones_total_mes = await db.scalar(
        select(func.count(Cotizacion.id_cotizacion)).where(Cotizacion.fecha_creacion >= inicio_mes)
    )
    cotizaciones_facturadas_mes = await db.scalar(
        select(func.count(Cotizacion.id_cotizacion)).where(
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
            Cotizacion.fecha_creacion >= inicio_mes,
        )
    )

    ingresos_val = money(ingresos_facturados_mes or 0)
    compras_val = money(compras_registradas_mes or 0)
    cartera_val = money(cuentas_por_cobrar or 0)
    caja_ingresos_val = money(caja_ingresos_mes or 0)
    caja_egresos_val = money(caja_egresos_mes or 0)
    cotizaciones_mes_val = int(cotizaciones_total_mes or 0)
    cotizaciones_facturadas_val = int(cotizaciones_facturadas_mes or 0)
    tickets_abiertos_val = int(tickets_abiertos or 0)

    ratio_compras_ingresos = percentage(compras_val, ingresos_val)
    ratio_cartera_ingresos = percentage(cartera_val, ingresos_val)
    ratio_egresos_caja_ingresos = percentage(caja_egresos_val, caja_ingresos_val)
    conversion_cotizaciones = percentage(cotizaciones_facturadas_val, cotizaciones_mes_val)
    carga_tickets_por_factura = (
        (tickets_abiertos_val / cotizaciones_facturadas_val)
        if cotizaciones_facturadas_val > 0
        else float(tickets_abiertos_val)
    )

    correlaciones = [
        DashboardCorrelationMetric(
            key="compras_vs_ingresos",
            label="Compras vs ingresos",
            value=money(ratio_compras_ingresos),
            unit="%",
            status="ok" if ratio_compras_ingresos <= 70 else "warning" if ratio_compras_ingresos <= 90 else "critical",
            detail="Mide que parte de lo facturado se esta yendo a compras del mes.",
        ),
        DashboardCorrelationMetric(
            key="cartera_vs_ingresos",
            label="Cartera vs facturacion",
            value=money(ratio_cartera_ingresos),
            unit="%",
            status="ok" if ratio_cartera_ingresos <= 60 else "warning" if ratio_cartera_ingresos <= 90 else "critical",
            detail="Mide el peso de cuentas por cobrar frente a los ingresos ya facturados.",
        ),
        DashboardCorrelationMetric(
            key="egresos_caja_vs_ingresos_caja",
            label="Egresos caja vs ingresos caja",
            value=money(ratio_egresos_caja_ingresos),
            unit="%",
            status="ok" if ratio_egresos_caja_ingresos <= 100 else "warning" if ratio_egresos_caja_ingresos <= 125 else "critical",
            detail="Detecta si caja chica esta drenando mas de lo que repone durante el mes.",
        ),
        DashboardCorrelationMetric(
            key="conversion_cotizaciones",
            label="Conversion de cotizaciones",
            value=money(conversion_cotizaciones),
            unit="%",
            status="ok" if conversion_cotizaciones >= 45 else "warning" if conversion_cotizaciones >= 25 else "critical",
            detail="Porcentaje de cotizaciones del mes que ya se facturaron.",
        ),
        DashboardCorrelationMetric(
            key="carga_tickets_por_factura",
            label="Carga tickets por factura",
            value=money(carga_tickets_por_factura),
            unit="x",
            status="ok" if carga_tickets_por_factura <= 2 else "warning" if carga_tickets_por_factura <= 4 else "critical",
            detail="Relacion entre tickets abiertos y cotizaciones ya facturadas en el mes.",
        ),
    ]

    return DashboardFinanceAnalytics(
        ingresos_facturados_mes=money(ingresos_facturados_mes or 0),
        compras_registradas_mes=money(compras_registradas_mes or 0),
        caja_ingresos_mes=money(caja_ingresos_mes or 0),
        caja_egresos_mes=money(caja_egresos_mes or 0),
        flujo_neto_mes=money(flujo_neto_mes or 0),
        cuentas_por_cobrar=money(cuentas_por_cobrar or 0),
        ordenes_pendientes_monto=money(ordenes_pendientes_monto or 0),
        margen_bruto_mes=money(margen_bruto_mes or 0),
        caja_chica_balance=money(caja_balance or 0),
        top_clientes=top_clientes,
        egresos_por_categoria=egresos_por_categoria,
        cartera_aging=cartera_aging,
        proximos_vencimientos=proximos_vencimientos,
        tendencia_mensual=tendencia_mensual,
        alertas=alertas,
        correlaciones=correlaciones,
    )
