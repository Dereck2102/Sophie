from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.caja_chica import MovimientoCajaChica, TipoMovimientoCajaEnum
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.caja_chica import CajaChicaResumenOut, MovimientoCajaChicaCreate, MovimientoCajaChicaOut

router = APIRouter(prefix="/caja-chica", tags=["Caja Chica"])


_ALLOWED_ROLES = (RolEnum.SUPERADMIN, RolEnum.ADMINISTRATIVO_CONTABLE)


def _signed_amount_expr() -> object:
    return case(
        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.INGRESO, MovimientoCajaChica.monto),
        (MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO, -MovimientoCajaChica.monto),
        else_=MovimientoCajaChica.monto,
    )


@router.get("/", response_model=list[MovimientoCajaChicaOut])
async def list_movimientos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(*_ALLOWED_ROLES))],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[MovimientoCajaChica]:
    result = await db.execute(
        select(MovimientoCajaChica)
        .order_by(MovimientoCajaChica.fecha.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/", response_model=MovimientoCajaChicaOut, status_code=status.HTTP_201_CREATED)
async def create_movimiento(
    body: MovimientoCajaChicaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(*_ALLOWED_ROLES))],
) -> MovimientoCajaChica:
    if body.monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")

    mov = MovimientoCajaChica(**body.model_dump())
    db.add(mov)
    await db.flush()
    return mov


@router.delete("/{id_movimiento}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_movimiento(
    id_movimiento: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(*_ALLOWED_ROLES))],
) -> None:
    result = await db.execute(
        select(MovimientoCajaChica).where(MovimientoCajaChica.id_movimiento == id_movimiento)
    )
    mov = result.scalar_one_or_none()
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    await db.delete(mov)
    await db.flush()


@router.get("/resumen", response_model=CajaChicaResumenOut)
async def get_resumen(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(*_ALLOWED_ROLES))],
) -> CajaChicaResumenOut:
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    balance_result = await db.execute(select(func.coalesce(func.sum(_signed_amount_expr()), 0)))
    balance_actual = float(balance_result.scalar_one() or 0)

    ingresos_mes_result = await db.execute(
        select(func.coalesce(func.sum(MovimientoCajaChica.monto), 0)).where(
            and_(
                MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.INGRESO,
                MovimientoCajaChica.fecha >= inicio_mes,
            )
        )
    )
    ingresos_mes = float(ingresos_mes_result.scalar_one() or 0)

    egresos_mes_result = await db.execute(
        select(func.coalesce(func.sum(MovimientoCajaChica.monto), 0)).where(
            and_(
                MovimientoCajaChica.tipo == TipoMovimientoCajaEnum.EGRESO,
                MovimientoCajaChica.fecha >= inicio_mes,
            )
        )
    )
    egresos_mes = float(egresos_mes_result.scalar_one() or 0)

    movimientos_mes_result = await db.execute(
        select(func.count(MovimientoCajaChica.id_movimiento)).where(
            MovimientoCajaChica.fecha >= inicio_mes
        )
    )
    movimientos_mes = int(movimientos_mes_result.scalar_one() or 0)

    return CajaChicaResumenOut(
        balance_actual=round(balance_actual, 2),
        ingresos_mes=round(ingresos_mes, 2),
        egresos_mes=round(egresos_mes, 2),
        movimientos_mes=movimientos_mes,
    )
