from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.infrastructure.models.caja_chica import TipoMovimientoCajaEnum


class MovimientoCajaChicaCreate(BaseModel):
    tipo: TipoMovimientoCajaEnum
    concepto: str
    categoria: Optional[str] = None
    monto: float
    responsable: Optional[str] = None
    observacion: Optional[str] = None


class MovimientoCajaChicaOut(BaseModel):
    id_movimiento: int
    tipo: TipoMovimientoCajaEnum
    concepto: str
    categoria: Optional[str] = None
    monto: float
    responsable: Optional[str] = None
    observacion: Optional[str] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class CajaChicaResumenOut(BaseModel):
    balance_actual: float
    ingresos_mes: float
    egresos_mes: float
    movimientos_mes: int
    fondo_mensual: float = 0
    disponible_mes: float = 0
