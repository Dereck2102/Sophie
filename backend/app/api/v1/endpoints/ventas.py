from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.inventario import Inventario, InventarioSerie, EstadoSerieEnum
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.infrastructure.models.ventas import (
    Cotizacion,
    DetalleCotizacion,
    EstadoCotizacionEnum,
    EstadoVentaEnum,
    Venta,
)
from app.schemas.ventas import (
    CotizacionCreate,
    CotizacionOut,
    CotizacionUpdate,
    FacturarVentaRequest,
    VentaOut,
)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def _next_numero_cotizacion(count: int) -> str:
    return f"COT-{count + 1:06d}"


@router.get("/cotizaciones", response_model=List[CotizacionOut])
async def list_cotizaciones(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Cotizacion]:
    q = (
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .offset(skip)
        .limit(limit)
        .order_by(Cotizacion.fecha_creacion.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/cotizaciones", response_model=CotizacionOut, status_code=201)
async def create_cotizacion(
    body: CotizacionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Cotizacion:
    count_result = await db.execute(select(Cotizacion))
    count = len(list(count_result.scalars().all()))
    numero = _next_numero_cotizacion(count)

    subtotal = 0.0
    cotizacion = Cotizacion(
        numero=numero,
        id_cliente=body.id_cliente,
        id_vendedor=current_user.id_usuario,
        notas=body.notas,
        fecha_vencimiento=body.fecha_vencimiento,
    )
    db.add(cotizacion)
    await db.flush()

    for d in body.detalles:
        sub = round(d.cantidad * d.precio_unitario * (1 - d.descuento / 100), 2)
        subtotal += sub
        db.add(
            DetalleCotizacion(
                id_cotizacion=cotizacion.id_cotizacion,
                id_producto=d.id_producto,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                descuento=d.descuento,
                subtotal=sub,
            )
        )

    impuesto = round(subtotal * 0.18, 2)
    cotizacion.subtotal = subtotal
    cotizacion.impuesto = impuesto
    cotizacion.total = round(subtotal + impuesto, 2)

    db.add(
        EventoCliente(
            id_cliente=body.id_cliente,
            tipo_evento="COTIZACION",
            descripcion=f"Cotización {numero} creada.",
        )
    )
    await db.flush()
    await db.refresh(cotizacion, ["detalles"])
    return cotizacion


@router.get("/cotizaciones/{id_cotizacion}", response_model=CotizacionOut)
async def get_cotizacion(
    id_cotizacion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Cotizacion:
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    return c


@router.patch("/cotizaciones/{id_cotizacion}", response_model=CotizacionOut)
async def update_cotizacion(
    id_cotizacion: int,
    body: CotizacionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Cotizacion:
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    if body.estado:
        c.estado = body.estado
    if body.notas is not None:
        c.notas = body.notas
    await db.flush()
    await db.refresh(c, ["detalles"])
    return c


@router.post("/cotizaciones/{id_cotizacion}/facturar", response_model=VentaOut)
async def facturar_cotizacion(
    id_cotizacion: int,
    body: FacturarVentaRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Venta:
    """
    Transactional: Marks cotizacion as FACTURADA, creates Venta,
    decrements stock and updates inventario_serie states (ACID).
    """
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    cotizacion = result.scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    if cotizacion.estado == EstadoCotizacionEnum.FACTURADA:
        raise HTTPException(status_code=400, detail="Already invoiced")

    # Discount stock
    for det in cotizacion.detalles:
        prod_result = await db.execute(
            select(Inventario).where(Inventario.id_producto == det.id_producto)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            if product.stock_actual < det.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product {product.codigo}",
                )
            product.stock_actual -= det.cantidad

            if product.requiere_serie:
                series_result = await db.execute(
                    select(InventarioSerie)
                    .where(
                        InventarioSerie.id_producto == det.id_producto,
                        InventarioSerie.estado == EstadoSerieEnum.DISPONIBLE,
                    )
                    .limit(det.cantidad)
                )
                series = list(series_result.scalars().all())
                for s in series:
                    s.estado = EstadoSerieEnum.VENDIDO

    cotizacion.estado = EstadoCotizacionEnum.FACTURADA

    venta = Venta(
        id_cotizacion=id_cotizacion,
        numero_factura=body.numero_factura,
        estado=EstadoVentaEnum.FACTURADA,
        fecha_factura=datetime.now(timezone.utc),
    )
    db.add(venta)

    db.add(
        EventoCliente(
            id_cliente=cotizacion.id_cliente,
            tipo_evento="FACTURA",
            descripcion=f"Factura {body.numero_factura} emitida.",
        )
    )
    await db.flush()
    return venta
