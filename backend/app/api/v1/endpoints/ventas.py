from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.money import money, percentage, to_decimal
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.cliente import Cliente
from app.infrastructure.models.inventario import Inventario, InventarioSerie, EstadoSerieEnum
from app.infrastructure.models.proyectos import Proyecto
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


def _tenant_id_for_user(current_user: Usuario) -> int | None:
    if current_user.rol == RolEnum.SUPERADMIN:
        return None
    return current_user.id_cliente


def _assert_cotizacion_tenant_access(current_user: Usuario, cotizacion: Cotizacion) -> None:
    tenant_id = _tenant_id_for_user(current_user)
    if tenant_id is None:
        return
    if cotizacion.tenant_id == tenant_id:
        return
    if cotizacion.tenant_id is None and cotizacion.id_cliente == tenant_id:
        return
    raise HTTPException(status_code=403, detail="No puedes acceder a cotizaciones de otro tenant")


async def _get_iva_rate(db: AsyncSession) -> float:
    result = await db.execute(
        select(ConfiguracionSistema.iva_default_percent).where(ConfiguracionSistema.id_configuracion == 1)
    )
    iva_percent = result.scalar_one_or_none()
    return float(to_decimal(max(0.0, float(iva_percent or 15))) / to_decimal(100))


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
    costo_materiales_total = to_decimal(0)
    margen_bruto_total = to_decimal(0)

    for detalle in cotizacion.detalles:
        costo_material_unitario = money(cost_map.get(detalle.id_producto, 0.0))
        cantidad = int(detalle.cantidad)
        costo_material_total = money(to_decimal(costo_material_unitario) * to_decimal(cantidad))
        subtotal = money(detalle.subtotal)
        precio_unitario = money(detalle.precio_unitario)
        descuento = money(detalle.descuento)
        precio_unitario_neto = money(to_decimal(precio_unitario) * (to_decimal(1) - (to_decimal(descuento) / to_decimal(100))))
        margen_unitario = money(to_decimal(precio_unitario_neto) - to_decimal(costo_material_unitario))
        margen_total = money(to_decimal(subtotal) - to_decimal(costo_material_total))
        rentabilidad_pct = percentage(margen_total, subtotal)

        costo_materiales_total += to_decimal(costo_material_total)
        margen_bruto_total += to_decimal(margen_total)

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

    costo_servicios_total = money(_service_cost_total(cotizacion))
    utilidad_neta_operativa = money(margen_bruto_total - to_decimal(costo_servicios_total))
    subtotal = money(cotizacion.subtotal)
    rentabilidad_total = percentage(utilidad_neta_operativa, subtotal)

    return CotizacionOut(
        id_cotizacion=cotizacion.id_cotizacion,
        numero=cotizacion.numero,
        id_cliente=cotizacion.id_cliente,
        id_vendedor=cotizacion.id_vendedor,
        id_proyecto=cotizacion.id_proyecto,
        estado=cotizacion.estado,
        subtotal=money(cotizacion.subtotal),
        impuesto=money(cotizacion.impuesto),
        total=money(cotizacion.total),
        costo_mano_obra=money(cotizacion.costo_mano_obra or 0),
        costo_movilizacion=money(cotizacion.costo_movilizacion or 0),
        costo_software=money(cotizacion.costo_software or 0),
        horas_soporte=money(cotizacion.horas_soporte or 0),
        tarifa_hora_soporte=money(cotizacion.tarifa_hora_soporte or 0),
        costo_servicios_total=costo_servicios_total,
        notas=cotizacion.notas,
        fecha_creacion=cotizacion.fecha_creacion,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        costo_materiales_total=money(costo_materiales_total),
        margen_bruto_total=money(margen_bruto_total),
        utilidad_neta_operativa=utilidad_neta_operativa,
        rentabilidad_pct=rentabilidad_total,
        detalles=detalles,
    )


def _service_cost_total(cotizacion: Cotizacion) -> float:
    mano_obra = to_decimal(cotizacion.costo_mano_obra or 0)
    movilizacion = to_decimal(cotizacion.costo_movilizacion or 0)
    software = to_decimal(cotizacion.costo_software or 0)
    horas = to_decimal(cotizacion.horas_soporte or 0)
    tarifa_hora = to_decimal(cotizacion.tarifa_hora_soporte or 0)
    return money(mano_obra + movilizacion + software + (horas * tarifa_hora))


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
    tenant_id = _tenant_id_for_user(current_user)
    q = (
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .offset(skip)
        .limit(limit)
        .order_by(Cotizacion.fecha_creacion.desc())
    )
    if tenant_id is not None:
        q = q.where(
            or_(
                Cotizacion.tenant_id == tenant_id,
                and_(Cotizacion.tenant_id.is_(None), Cotizacion.id_cliente == tenant_id),
            )
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
    tenant_id = _tenant_id_for_user(current_user)

    cliente_result = await db.execute(select(Cliente).where(Cliente.id_cliente == body.id_cliente))
    cliente = cliente_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")

    if tenant_id is not None:
        cliente_belongs_to_tenant = cliente.tenant_id == tenant_id or (
            cliente.tenant_id is None and cliente.id_cliente == tenant_id
        )
        if not cliente_belongs_to_tenant:
            raise HTTPException(status_code=403, detail="No puedes crear cotizaciones para otro tenant")

    # Use MAX(id)+1 rather than COUNT to avoid duplicate numbers after deletions
    max_id_result = await db.execute(select(func.coalesce(func.max(Cotizacion.id_cotizacion), 0)))
    max_id = int(max_id_result.scalar_one() or 0)
    numero = f"COT-{max_id + 1:06d}"

    if body.id_proyecto is not None:
        proyecto_result = await db.execute(
            select(Proyecto).where(Proyecto.id_proyecto == body.id_proyecto)
        )
        proyecto = proyecto_result.scalar_one_or_none()
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto not found")
        if proyecto.id_cliente != body.id_cliente:
            raise HTTPException(
                status_code=400,
                detail="El proyecto seleccionado no pertenece al cliente de la cotización",
            )

    cotizacion = Cotizacion(
        numero=numero,
        tenant_id=tenant_id if tenant_id is not None else cliente.tenant_id,
        id_cliente=body.id_cliente,
        id_vendedor=current_user.id_usuario,
        id_proyecto=body.id_proyecto,
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

    subtotal_dec = to_decimal(_service_cost_total(cotizacion))

    for d in body.detalles:
        sub = money(
            to_decimal(d.cantidad)
            * to_decimal(d.precio_unitario)
            * (to_decimal(1) - (to_decimal(d.descuento) / to_decimal(100)))
        )
        subtotal_dec += to_decimal(sub)
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
    impuesto = money(subtotal_dec * to_decimal(iva_rate))
    cotizacion.subtotal = money(subtotal_dec)
    cotizacion.impuesto = impuesto
    cotizacion.total = money(subtotal_dec + to_decimal(impuesto))

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
    tenant_id = _tenant_id_for_user(current_user)
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    if tenant_id is not None:
        _assert_cotizacion_tenant_access(current_user, c)
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
    tenant_id = _tenant_id_for_user(current_user)
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cotizacion == id_cotizacion)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cotizacion not found")
    if tenant_id is not None:
        _assert_cotizacion_tenant_access(current_user, c)
    if body.estado:
        c.estado = body.estado
    if body.id_proyecto is not None:
        proyecto_result = await db.execute(
            select(Proyecto).where(Proyecto.id_proyecto == body.id_proyecto)
        )
        proyecto = proyecto_result.scalar_one_or_none()
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto not found")
        if proyecto.id_cliente != c.id_cliente:
            raise HTTPException(
                status_code=400,
                detail="El proyecto seleccionado no pertenece al cliente de la cotización",
            )
        c.id_proyecto = body.id_proyecto
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
        detalle_subtotal = sum((to_decimal(d.subtotal or 0) for d in c.detalles), start=to_decimal(0))
        c.subtotal = money(detalle_subtotal + to_decimal(_service_cost_total(c)))
        iva_rate = await _get_iva_rate(db)
        c.impuesto = money(to_decimal(c.subtotal) * to_decimal(iva_rate))
        c.total = money(to_decimal(c.subtotal) + to_decimal(c.impuesto))

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
    _assert_cotizacion_tenant_access(current_user, cotizacion)
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
    _assert_cotizacion_tenant_access(current_user, cotizacion)

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
