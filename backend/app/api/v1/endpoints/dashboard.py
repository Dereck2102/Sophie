from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
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


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DashboardStats:
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

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
    revenue_mes = int(float(revenue_result.scalar_one() or 0))

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
    margen_bruto_mes = float(margen_result.scalar_one() or 0)

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
    )
    caja_chica_balance = float(caja_balance_result.scalar_one() or 0)

    caja_egresos_result = await db.execute(
        select(func.coalesce(func.sum(MovimientoCajaChica.monto), 0)).where(
            MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO,
            MovimientoCajaChica.fecha >= inicio_mes,
        )
    )
    caja_chica_egresos_mes = float(caja_egresos_result.scalar_one() or 0)

    return DashboardStats(
        total_clientes=total_clientes,
        cotizaciones_mes=cotizaciones_mes,
        tickets_abiertos=tickets_abiertos,
        productos_bajo_stock=productos_bajo_stock,
        revenue_mes=revenue_mes,
        proyectos_activos=proyectos_activos,
        margen_bruto_mes=round(margen_bruto_mes, 2),
        caja_chica_balance=round(caja_chica_balance, 2),
        caja_chica_egresos_mes=round(caja_chica_egresos_mes, 2),
    )


@router.get("/analytics", response_model=DashboardFinanceAnalytics)
async def get_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DashboardFinanceAnalytics:
    _ = current_user
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

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
        .where(MovimientoCajaChica.fecha >= inicio_mes)
        .group_by(MovimientoCajaChica.tipo)
    )
    caja_map = {tipo: float(total or 0) for tipo, total in caja_totales.all()}
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
    )

    flujo_neto_mes = float(ingresos_facturados_mes or 0) + float(caja_ingresos_mes or 0) - float(compras_registradas_mes or 0) - float(caja_egresos_mes or 0)

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

    total_top = sum(float(total or 0) for _, total in top_client_data)
    top_clientes = [
        DashboardTopClient(
            id_cliente=int(client_id),
            nombre=_client_display_name(client_map.get(int(client_id))),
            total_facturado=round(float(total or 0), 2),
            participacion_pct=round((float(total or 0) / total_top * 100) if total_top else 0, 2),
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
        DashboardExpenseCategory(categoria=str(categoria), total=round(float(total or 0), 2))
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
        "Vigente": {"total": 0.0, "cantidad": 0},
        "Vencido 1-30": {"total": 0.0, "cantidad": 0},
        "Vencido 31-60": {"total": 0.0, "cantidad": 0},
        "Vencido 61+": {"total": 0.0, "cantidad": 0},
        "Sin vencimiento": {"total": 0.0, "cantidad": 0},
    }

    proximos_vencimientos: list[DashboardReceivableDueItem] = []
    for cotizacion in receivables:
        total = float(cotizacion.total or 0)
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
                        total=round(total, 2),
                        fecha_vencimiento=fecha_vencimiento.date().isoformat(),
                        dias_para_vencer=dias_para_vencer,
                        dias_vencido=dias_vencido,
                    )
                )

        aging_totals[bucket]["total"] += total
        aging_totals[bucket]["cantidad"] += 1

    cartera_aging = [
        DashboardReceivableBucket(
            bucket=bucket,
            total=round(values["total"], 2),
            cantidad=int(values["cantidad"]),
        )
        for bucket, values in aging_totals.items()
    ]

    tendencia_mensual: list[DashboardTrendPoint] = []
    for offset in range(-5, 1):
        start, end, label = _month_window(inicio_mes, offset)

        ingresos_periodo = await db.scalar(
            select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
                Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
                Cotizacion.fecha_creacion >= start,
                Cotizacion.fecha_creacion < end,
            )
        )
        compras_periodo = await db.scalar(
            select(func.coalesce(func.sum(OrdenCompra.total), 0)).where(
                OrdenCompra.fecha_creacion >= start,
                OrdenCompra.fecha_creacion < end,
                OrdenCompra.estado != EstadoOrdenEnum.CANCELADA,
            )
        )
        caja_periodo_rows = await db.execute(
            select(
                MovimientoCajaChica.tipo,
                func.coalesce(func.sum(MovimientoCajaChica.monto), 0),
            )
            .where(MovimientoCajaChica.fecha >= start, MovimientoCajaChica.fecha < end)
            .group_by(MovimientoCajaChica.tipo)
        )
        caja_periodo_map = {tipo: float(total or 0) for tipo, total in caja_periodo_rows.all()}
        caja_ingresos = caja_periodo_map.get(TipoMovimientoCajaEnum.INGRESO, 0.0)
        caja_egresos = caja_periodo_map.get(TipoMovimientoCajaEnum.EGRESO, 0.0)

        tendencia_mensual.append(
            DashboardTrendPoint(
                label=label,
                ingresos=round(float(ingresos_periodo or 0), 2),
                compras=round(float(compras_periodo or 0), 2),
                caja_ingresos=round(float(caja_ingresos or 0), 2),
                caja_egresos=round(float(caja_egresos or 0), 2),
                flujo_neto=round(float(ingresos_periodo or 0) + float(caja_ingresos or 0) - float(compras_periodo or 0) - float(caja_egresos or 0), 2),
            )
        )

    alertas: list[DashboardAlert] = []
    if float(caja_balance or 0) <= 0:
        alertas.append(
            DashboardAlert(
                severity="critical",
                title="Caja chica comprometida",
                detail="El balance de caja chica esta en cero o negativo. Conviene revisar reposiciones y egresos urgentes.",
                link="/caja-chica",
            )
        )
    if float(cuentas_por_cobrar or 0) > max(float(ingresos_facturados_mes or 0) * 0.75, 500):
        alertas.append(
            DashboardAlert(
                severity="warning",
                title="Cobros pendientes altos",
                detail="Las cotizaciones aprobadas o enviadas ya superan un umbral prudente frente a la facturacion del mes.",
                link="/ventas",
            )
        )
    if float(ordenes_pendientes_monto or 0) > float(ingresos_facturados_mes or 0):
        alertas.append(
            DashboardAlert(
                severity="warning",
                title="Compromiso de compras elevado",
                detail="El monto de ordenes pendientes es mayor que la facturacion registrada del mes.",
                link="/compras",
            )
        )
    if float(caja_egresos_mes or 0) > max(float(caja_ingresos_mes or 0) * 1.25, 300):
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

    return DashboardFinanceAnalytics(
        ingresos_facturados_mes=round(float(ingresos_facturados_mes or 0), 2),
        compras_registradas_mes=round(float(compras_registradas_mes or 0), 2),
        caja_ingresos_mes=round(float(caja_ingresos_mes or 0), 2),
        caja_egresos_mes=round(float(caja_egresos_mes or 0), 2),
        flujo_neto_mes=round(float(flujo_neto_mes or 0), 2),
        cuentas_por_cobrar=round(float(cuentas_por_cobrar or 0), 2),
        ordenes_pendientes_monto=round(float(ordenes_pendientes_monto or 0), 2),
        margen_bruto_mes=round(float(margen_bruto_mes or 0), 2),
        caja_chica_balance=round(float(caja_balance or 0), 2),
        top_clientes=top_clientes,
        egresos_por_categoria=egresos_por_categoria,
        cartera_aging=cartera_aging,
        proximos_vencimientos=proximos_vencimientos,
        tendencia_mensual=tendencia_mensual,
        alertas=alertas,
    )
