from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.inventario import Inventario, InventarioSerie, EstadoSerieEnum
from app.infrastructure.models.sistema import ConfiguracionSistema
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


async def _get_iva_rate(db: AsyncSession) -> float:
    result = await db.execute(
        select(ConfiguracionSistema.iva_default_percent).where(ConfiguracionSistema.id_configuracion == 1)
    )
    iva_percent = result.scalar_one_or_none()
    return max(0.0, float(iva_percent or 15)) / 100


async def _get_cost_map(db: AsyncSession, product_ids: set[int]) -> dict[int, float]:
    if not product_ids:
        return {}
    result = await db.execute(
        select(Inventario.id_producto, Inventario.costo_adquisicion).where(
            Inventario.id_producto.in_(product_ids)
        )
    )
    rows = result.all()
    return {int(product_id): float(cost or 0) for product_id, cost in rows}


def _serialize_cotizacion(cotizacion: Cotizacion, cost_map: dict[int, float]) -> CotizacionOut:
    detalles: list = []
    costo_materiales_total = 0.0
    margen_bruto_total = 0.0

    for detalle in cotizacion.detalles:
        costo_material_unitario = float(cost_map.get(detalle.id_producto, 0.0))
        cantidad = int(detalle.cantidad)
        costo_material_total = round(costo_material_unitario * cantidad, 2)
        subtotal = float(detalle.subtotal)
        precio_unitario = float(detalle.precio_unitario)
        descuento = float(detalle.descuento)
        precio_unitario_neto = round(precio_unitario * (1 - descuento / 100), 2)
        margen_unitario = round(precio_unitario_neto - costo_material_unitario, 2)
        margen_total = round(subtotal - costo_material_total, 2)
        rentabilidad_pct = round((margen_total / subtotal) * 100, 2) if subtotal > 0 else 0.0

        costo_materiales_total += costo_material_total
        margen_bruto_total += margen_total

        detalles.append(
            {
                "id_detalle": detalle.id_detalle,
                "id_producto": detalle.id_producto,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "descuento": descuento,
                "subtotal": subtotal,
                "costo_material_unitario": costo_material_unitario,
                "costo_material_total": costo_material_total,
                "margen_unitario": margen_unitario,
                "margen_total": margen_total,
                "rentabilidad_pct": rentabilidad_pct,
            }
        )

    costo_servicios_total = round(_service_cost_total(cotizacion), 2)
    utilidad_neta_operativa = round(margen_bruto_total - costo_servicios_total, 2)
    subtotal = float(cotizacion.subtotal)
    rentabilidad_total = round((utilidad_neta_operativa / subtotal) * 100, 2) if subtotal > 0 else 0.0

    return CotizacionOut(
        id_cotizacion=cotizacion.id_cotizacion,
        numero=cotizacion.numero,
        id_cliente=cotizacion.id_cliente,
        id_vendedor=cotizacion.id_vendedor,
        estado=cotizacion.estado,
        subtotal=float(cotizacion.subtotal),
        impuesto=float(cotizacion.impuesto),
        total=float(cotizacion.total),
        costo_mano_obra=float(cotizacion.costo_mano_obra or 0),
        costo_movilizacion=float(cotizacion.costo_movilizacion or 0),
        costo_software=float(cotizacion.costo_software or 0),
        horas_soporte=float(cotizacion.horas_soporte or 0),
        tarifa_hora_soporte=float(cotizacion.tarifa_hora_soporte or 0),
        costo_servicios_total=costo_servicios_total,
        notas=cotizacion.notas,
        fecha_creacion=cotizacion.fecha_creacion,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        costo_materiales_total=round(costo_materiales_total, 2),
        margen_bruto_total=round(margen_bruto_total, 2),
        utilidad_neta_operativa=utilidad_neta_operativa,
        rentabilidad_pct=rentabilidad_total,
        detalles=detalles,
    )


def _service_cost_total(cotizacion: Cotizacion) -> float:
    mano_obra = float(cotizacion.costo_mano_obra or 0)
    movilizacion = float(cotizacion.costo_movilizacion or 0)
    software = float(cotizacion.costo_software or 0)
    horas = float(cotizacion.horas_soporte or 0)
    tarifa_hora = float(cotizacion.tarifa_hora_soporte or 0)
    return mano_obra + movilizacion + software + (horas * tarifa_hora)


def _next_numero_cotizacion(count: int) -> str:
    return f"COT-{count + 1:06d}"


@router.get("/cotizaciones", response_model=List[CotizacionOut])
async def list_cotizaciones(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.EJECUTIVO, RolEnum.SUPERADMIN))
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[CotizacionOut]:
    q = (
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .offset(skip)
        .limit(limit)
        .order_by(Cotizacion.fecha_creacion.desc())
    )
    result = await db.execute(q)
    cotizaciones = list(result.scalars().all())
    product_ids = {d.id_producto for c in cotizaciones for d in c.detalles}
    cost_map = await _get_cost_map(db, product_ids)
    return [_serialize_cotizacion(c, cost_map) for c in cotizaciones]


@router.post("/cotizaciones", response_model=CotizacionOut, status_code=201)
async def create_cotizacion(
    body: CotizacionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.EJECUTIVO, RolEnum.SUPERADMIN))
    ],
) -> CotizacionOut:
    count_result = await db.execute(select(func.count(Cotizacion.id_cotizacion)))
    count = count_result.scalar_one() or 0
    numero = _next_numero_cotizacion(count)

    subtotal = 0.0
    cotizacion = Cotizacion(
        numero=numero,
        id_cliente=body.id_cliente,
        id_vendedor=current_user.id_usuario,
        costo_mano_obra=body.costo_mano_obra,
        costo_movilizacion=body.costo_movilizacion,
        costo_software=body.costo_software,
        horas_soporte=body.horas_soporte,
        tarifa_hora_soporte=body.tarifa_hora_soporte,
        notas=body.notas,
        fecha_vencimiento=body.fecha_vencimiento,
    )
    db.add(cotizacion)
    await db.flush()

    subtotal = _service_cost_total(cotizacion)

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

    iva_rate = await _get_iva_rate(db)
    impuesto = round(subtotal * iva_rate, 2)
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
    product_ids = {d.id_producto for d in cotizacion.detalles}
    cost_map = await _get_cost_map(db, product_ids)
    return _serialize_cotizacion(cotizacion, cost_map)


@router.get("/cotizaciones/{id_cotizacion}", response_model=CotizacionOut)
async def get_cotizacion(
    id_cotizacion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.EJECUTIVO, RolEnum.SUPERADMIN))
    ],
) -> CotizacionOut:
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    product_ids = {d.id_producto for d in c.detalles}
    cost_map = await _get_cost_map(db, product_ids)
    return _serialize_cotizacion(c, cost_map)


@router.patch("/cotizaciones/{id_cotizacion}", response_model=CotizacionOut)
async def update_cotizacion(
    id_cotizacion: int,
    body: CotizacionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CotizacionOut:
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

    if body.costo_mano_obra is not None:
        c.costo_mano_obra = body.costo_mano_obra
    if body.costo_movilizacion is not None:
        c.costo_movilizacion = body.costo_movilizacion
    if body.costo_software is not None:
        c.costo_software = body.costo_software
    if body.horas_soporte is not None:
        c.horas_soporte = body.horas_soporte
    if body.tarifa_hora_soporte is not None:
        c.tarifa_hora_soporte = body.tarifa_hora_soporte

    if any(
        value is not None
        for value in (
            body.costo_mano_obra,
            body.costo_movilizacion,
            body.costo_software,
            body.horas_soporte,
            body.tarifa_hora_soporte,
        )
    ):
        detalle_subtotal = sum(float(d.subtotal or 0) for d in c.detalles)
        c.subtotal = round(detalle_subtotal + _service_cost_total(c), 2)
        iva_rate = await _get_iva_rate(db)
        c.impuesto = round(float(c.subtotal) * iva_rate, 2)
        c.total = round(float(c.subtotal) + float(c.impuesto), 2)

    await db.flush()
    await db.refresh(c, ["detalles"])
    product_ids = {d.id_producto for d in c.detalles}
    cost_map = await _get_cost_map(db, product_ids)
    return _serialize_cotizacion(c, cost_map)


@router.post("/cotizaciones/{id_cotizacion}/facturar", response_model=VentaOut)
async def facturar_cotizacion(
    id_cotizacion: int,
    body: FacturarVentaRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.EJECUTIVO, RolEnum.SUPERADMIN))
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


@router.delete("/cotizaciones/{id_cotizacion}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_cotizacion(
    id_cotizacion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> None:
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles), selectinload(Cotizacion.venta))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    cotizacion = result.scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotizacion not found")

    await db.execute(
        delete(Venta)
        .where(Venta.id_cotizacion == id_cotizacion)
        .execution_options(synchronize_session=False)
    )
    await db.flush()

    await db.execute(
        delete(DetalleCotizacion)
        .where(DetalleCotizacion.id_cotizacion == id_cotizacion)
        .execution_options(synchronize_session=False)
    )
    await db.flush()

    await db.execute(
        delete(Cotizacion)
        .where(Cotizacion.id_cotizacion == id_cotizacion)
        .execution_options(synchronize_session=False)
    )
    await db.flush()
