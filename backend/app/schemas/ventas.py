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
    costo_material_unitario: float = 0
    costo_material_total: float = 0
    margen_unitario: float = 0
    margen_total: float = 0
    rentabilidad_pct: float = 0

    model_config = {"from_attributes": True}


class CotizacionCreate(BaseModel):
    id_cliente: int
    notas: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    costo_mano_obra: float = 0
    costo_movilizacion: float = 0
    costo_software: float = 0
    horas_soporte: float = 0
    tarifa_hora_soporte: float = 0
    detalles: List[DetalleCotizacionCreate]


class CotizacionUpdate(BaseModel):
    estado: Optional[EstadoCotizacionEnum] = None
    notas: Optional[str] = None
    costo_mano_obra: Optional[float] = None
    costo_movilizacion: Optional[float] = None
    costo_software: Optional[float] = None
    horas_soporte: Optional[float] = None
    tarifa_hora_soporte: Optional[float] = None
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
    costo_mano_obra: float = 0
    costo_movilizacion: float = 0
    costo_software: float = 0
    horas_soporte: float = 0
    tarifa_hora_soporte: float = 0
    costo_servicios_total: float = 0
    notas: Optional[str] = None
    fecha_creacion: datetime
    fecha_vencimiento: Optional[datetime] = None
    costo_materiales_total: float = 0
    margen_bruto_total: float = 0
    utilidad_neta_operativa: float = 0
    rentabilidad_pct: float = 0
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
