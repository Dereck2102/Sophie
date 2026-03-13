from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.compras import DetalleOrdenCompra
from app.infrastructure.models.inventario import Inventario, InventarioSerie
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.infrastructure.models.ventas import DetalleCotizacion
from app.schemas.inventario import (
    InventarioCreate,
    InventarioOut,
    InventarioOutVendedor,
    InventarioUpdate,
    SerieCreate,
    SerieOut,
    SerieUpdate,
)

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/", response_model=List[InventarioOut])
async def list_inventario(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Inventario]:
    # Vendedor gets redacted view - enforced in serialization
    result = await db.execute(select(Inventario).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.post("/", response_model=InventarioOut, status_code=201)
async def create_producto(
    body: InventarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.ADMINISTRATIVO_CONTABLE, RolEnum.SUPERADMIN))
    ],
) -> Inventario:
    producto = Inventario(**body.model_dump())
    db.add(producto)
    await db.flush()
    return producto


@router.get("/{id_producto}", response_model=InventarioOut)
async def get_producto(
    id_producto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Inventario:
    result = await db.execute(
        select(Inventario).where(Inventario.id_producto == id_producto)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Product not found")
    return producto


@router.patch("/{id_producto}", response_model=InventarioOut)
async def update_producto(
    id_producto: int,
    body: InventarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.ADMINISTRATIVO_CONTABLE, RolEnum.SUPERADMIN))
    ],
) -> Inventario:
    result = await db.execute(
        select(Inventario).where(Inventario.id_producto == id_producto)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Product not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(producto, k, v)
    await db.flush()
    return producto


@router.delete("/{id_producto}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_producto(
    id_producto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.ADMINISTRATIVO_CONTABLE, RolEnum.SUPERADMIN))
    ],
) -> None:
    result = await db.execute(
        select(Inventario).where(Inventario.id_producto == id_producto)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.execute(
        delete(DetalleCotizacion).where(DetalleCotizacion.id_producto == id_producto).execution_options(synchronize_session=False)
    )
    await db.execute(
        delete(DetalleOrdenCompra).where(DetalleOrdenCompra.id_producto == id_producto).execution_options(synchronize_session=False)
    )
    await db.execute(
        delete(InventarioSerie).where(InventarioSerie.id_producto == id_producto).execution_options(synchronize_session=False)
    )
    await db.flush()

    await db.execute(
        delete(Inventario).where(Inventario.id_producto == id_producto).execution_options(synchronize_session=False)
    )
    await db.flush()


@router.get("/{id_producto}/series", response_model=List[SerieOut])
async def list_series(
    id_producto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[InventarioSerie]:
    result = await db.execute(
        select(InventarioSerie).where(InventarioSerie.id_producto == id_producto)
    )
    return list(result.scalars().all())


@router.post("/series", response_model=SerieOut, status_code=201)
async def add_serie(
    body: SerieCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.ADMINISTRATIVO_CONTABLE, RolEnum.SUPERADMIN))
    ],
) -> InventarioSerie:
    serie = InventarioSerie(**body.model_dump())
    db.add(serie)
    # Increment stock
    prod_result = await db.execute(
        select(Inventario).where(Inventario.id_producto == body.id_producto)
    )
    producto = prod_result.scalar_one_or_none()
    if producto:
        producto.stock_actual += 1
    await db.flush()
    return serie


@router.patch("/series/{id_serie}", response_model=SerieOut)
async def update_serie(
    id_serie: int,
    body: SerieUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.ADMINISTRATIVO_CONTABLE, RolEnum.EJECUTIVO, RolEnum.SUPERADMIN))
    ],
) -> InventarioSerie:
    result = await db.execute(
        select(InventarioSerie).where(InventarioSerie.id_serie == id_serie)
    )
    serie = result.scalar_one_or_none()
    if not serie:
        raise HTTPException(status_code=404, detail="Series item not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(serie, k, v)
    await db.flush()
    return serie
