from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.compras import (
    DetalleOrdenCompra,
    EstadoOrdenEnum,
    OrdenCompra,
)
from app.infrastructure.models.inventario import Inventario
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.compras import (
    OrdenCompraCreate,
    OrdenCompraOut,
    OrdenCompraUpdate,
    RecibirOrdenRequest,
)

router = APIRouter(prefix="/compras", tags=["Compras & Proveedores"])


def _next_numero_orden(count: int) -> str:
    return f"OC-{count + 1:06d}"


@router.get("/ordenes", response_model=List[OrdenCompraOut])
async def list_ordenes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.COMPRADOR, RolEnum.ADMIN))
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[OrdenCompra]:
    result = await db.execute(
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.detalles))
        .offset(skip)
        .limit(limit)
        .order_by(OrdenCompra.fecha_creacion.desc())
    )
    return list(result.scalars().all())


@router.post("/ordenes", response_model=OrdenCompraOut, status_code=status.HTTP_201_CREATED)
async def create_orden(
    body: OrdenCompraCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.COMPRADOR, RolEnum.ADMIN))
    ],
) -> OrdenCompra:
    count_result = await db.execute(select(func.count(OrdenCompra.id_orden)))
    count = count_result.scalar_one() or 0
    numero = _next_numero_orden(count)

    total = 0.0
    orden = OrdenCompra(
        numero=numero,
        id_proveedor=body.id_proveedor,
        id_comprador=current_user.id_usuario,
        notas=body.notas,
        fecha_entrega_esperada=body.fecha_entrega_esperada,
    )
    db.add(orden)
    await db.flush()

    for d in body.detalles:
        sub = round(d.cantidad_pedida * d.precio_unitario, 2)
        total += sub
        db.add(
            DetalleOrdenCompra(
                id_orden=orden.id_orden,
                id_producto=d.id_producto,
                cantidad_pedida=d.cantidad_pedida,
                precio_unitario=d.precio_unitario,
                subtotal=sub,
            )
        )

    orden.total = round(total, 2)
    await db.flush()
    await db.refresh(orden, ["detalles"])
    return orden


@router.get("/ordenes/{id_orden}", response_model=OrdenCompraOut)
async def get_orden(
    id_orden: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.COMPRADOR, RolEnum.ADMIN))
    ],
) -> OrdenCompra:
    result = await db.execute(
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.detalles))
        .where(OrdenCompra.id_orden == id_orden)
    )
    orden = result.scalar_one_or_none()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de compra not found")
    return orden


@router.patch("/ordenes/{id_orden}", response_model=OrdenCompraOut)
async def update_orden(
    id_orden: int,
    body: OrdenCompraUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.COMPRADOR, RolEnum.ADMIN))
    ],
) -> OrdenCompra:
    result = await db.execute(
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.detalles))
        .where(OrdenCompra.id_orden == id_orden)
    )
    orden = result.scalar_one_or_none()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de compra not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(orden, k, v)
    await db.flush()
    await db.refresh(orden, ["detalles"])
    return orden


@router.post("/ordenes/{id_orden}/recibir", response_model=OrdenCompraOut)
async def recibir_orden(
    id_orden: int,
    body: RecibirOrdenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.COMPRADOR, RolEnum.ADMIN))
    ],
) -> OrdenCompra:
    """
    Register partial or total receipt of a purchase order.
    Updates received quantities and increments inventory stock.
    """
    result = await db.execute(
        select(OrdenCompra)
        .options(selectinload(OrdenCompra.detalles))
        .where(OrdenCompra.id_orden == id_orden)
    )
    orden = result.scalar_one_or_none()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de compra not found")
    if orden.estado == EstadoOrdenEnum.CANCELADA:
        raise HTTPException(status_code=400, detail="Cannot receive a cancelled order")

    detalle_map = {d.id_detalle: d for d in orden.detalles}
    total_completo = True

    for rec in body.detalles:
        det = detalle_map.get(rec.id_detalle)
        if not det:
            raise HTTPException(
                status_code=404, detail=f"Detalle {rec.id_detalle} not found in this order"
            )
        det.cantidad_recibida = min(det.cantidad_recibida + rec.cantidad_recibida, det.cantidad_pedida)

        # Update stock
        prod_result = await db.execute(
            select(Inventario).where(Inventario.id_producto == det.id_producto)
        )
        producto = prod_result.scalar_one_or_none()
        if producto:
            producto.stock_actual += rec.cantidad_recibida

    # Determine new order status
    for det in orden.detalles:
        if det.cantidad_recibida < det.cantidad_pedida:
            total_completo = False
            break

    orden.estado = (
        EstadoOrdenEnum.RECIBIDA_TOTAL if total_completo else EstadoOrdenEnum.RECIBIDA_PARCIAL
    )
    await db.flush()
    await db.refresh(orden, ["detalles"])
    return orden
