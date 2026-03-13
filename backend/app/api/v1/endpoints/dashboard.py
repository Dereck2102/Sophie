from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.infrastructure.models.cliente import Cliente, EstadoClienteEnum
from app.infrastructure.models.caja_chica import MovimientoCajaChica, TipoMovimientoCajaEnum
from app.infrastructure.models.inventario import Inventario
from app.infrastructure.models.proyectos import EstadoProyectoEnum, Proyecto
from app.infrastructure.models.tickets import EstadoTicketEnum, Ticket
from app.infrastructure.models.usuario import Usuario
from app.infrastructure.models.ventas import Cotizacion, DetalleCotizacion, EstadoCotizacionEnum
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


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
