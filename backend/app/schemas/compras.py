from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.infrastructure.models.compras import EstadoOrdenEnum


class DetalleOrdenCreate(BaseModel):
    id_producto: int
    cantidad_pedida: int
    precio_unitario: float


class DetalleOrdenOut(BaseModel):
    id_detalle: int
    id_producto: int
    cantidad_pedida: int
    cantidad_recibida: int
    precio_unitario: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrdenCompraCreate(BaseModel):
    id_proveedor: int
    notas: Optional[str] = None
    fecha_entrega_esperada: Optional[datetime] = None
    detalles: List[DetalleOrdenCreate]


class OrdenCompraUpdate(BaseModel):
    estado: Optional[EstadoOrdenEnum] = None
    notas: Optional[str] = None
    fecha_entrega_esperada: Optional[datetime] = None


class OrdenCompraOut(BaseModel):
    id_orden: int
    numero: str
    id_proveedor: int
    id_comprador: int
    estado: EstadoOrdenEnum
    total: float
    notas: Optional[str] = None
    fecha_creacion: datetime
    fecha_entrega_esperada: Optional[datetime] = None
    detalles: List[DetalleOrdenOut] = []

    model_config = {"from_attributes": True}


class DetalleRecepcion(BaseModel):
    id_detalle: int
    cantidad_recibida: int


class RecibirOrdenRequest(BaseModel):
    detalles: List[DetalleRecepcion]
