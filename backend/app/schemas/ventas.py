from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.infrastructure.models.ventas import EstadoCotizacionEnum, EstadoVentaEnum


class DetalleCotizacionCreate(BaseModel):
    id_producto: int
    cantidad: int = 1
    precio_unitario: float
    descuento: float = 0


class DetalleCotizacionOut(DetalleCotizacionCreate):
    id_detalle: int
    subtotal: float

    model_config = {"from_attributes": True}


class CotizacionCreate(BaseModel):
    id_cliente: int
    notas: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    detalles: List[DetalleCotizacionCreate]


class CotizacionUpdate(BaseModel):
    estado: Optional[EstadoCotizacionEnum] = None
    notas: Optional[str] = None
    detalles: Optional[List[DetalleCotizacionCreate]] = None


class CotizacionOut(BaseModel):
    id_cotizacion: int
    numero: str
    id_cliente: int
    id_vendedor: int
    estado: EstadoCotizacionEnum
    subtotal: float
    impuesto: float
    total: float
    notas: Optional[str] = None
    fecha_creacion: datetime
    fecha_vencimiento: Optional[datetime] = None
    detalles: List[DetalleCotizacionOut] = []

    model_config = {"from_attributes": True}


class VentaOut(BaseModel):
    id_venta: int
    id_cotizacion: int
    numero_factura: Optional[str] = None
    estado: EstadoVentaEnum
    fecha_venta: datetime
    fecha_factura: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FacturarVentaRequest(BaseModel):
    numero_factura: str
