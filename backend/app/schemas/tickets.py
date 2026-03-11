from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.infrastructure.models.tickets import EstadoTicketEnum, PrioridadEnum, TipoTicketEnum


class TicketCreate(BaseModel):
    tipo: TipoTicketEnum
    id_cliente: int
    id_tecnico: Optional[int] = None
    prioridad: PrioridadEnum = PrioridadEnum.MEDIA
    titulo: str
    descripcion: Optional[str] = None


class TicketUpdate(BaseModel):
    id_tecnico: Optional[int] = None
    prioridad: Optional[PrioridadEnum] = None
    estado: Optional[EstadoTicketEnum] = None
    descripcion: Optional[str] = None


class TicketOut(BaseModel):
    id_ticket: int
    numero: str
    tipo: TipoTicketEnum
    id_cliente: int
    id_tecnico: Optional[int] = None
    prioridad: PrioridadEnum
    estado: EstadoTicketEnum
    titulo: str
    descripcion: Optional[str] = None
    fecha_creacion: datetime
    fecha_cierre: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReparacionUpdate(BaseModel):
    equipo_descripcion: Optional[str] = None
    numero_serie_equipo: Optional[str] = None
    diagnostico: Optional[str] = None
    costo_reparacion: Optional[float] = None


class ReparacionOut(BaseModel):
    id_ticket: int
    equipo_descripcion: Optional[str] = None
    numero_serie_equipo: Optional[str] = None
    diagnostico: Optional[str] = None
    fotos_urls: Optional[str] = None
    costo_reparacion: Optional[float] = None
    repuestos: List["RepuestoUsadoOut"] = []

    model_config = {"from_attributes": True}


class RepuestoUsadoCreate(BaseModel):
    id_producto: int
    id_serie: Optional[int] = None
    cantidad: int = 1
    precio_unitario: float = 0


class RepuestoUsadoOut(RepuestoUsadoCreate):
    id_repuesto: int

    model_config = {"from_attributes": True}


class IncidenciaITOut(BaseModel):
    id_ticket: int
    id_sla: Optional[int] = None
    fecha_limite_respuesta: Optional[datetime] = None
    fecha_limite_resolucion: Optional[datetime] = None
    fecha_primera_respuesta: Optional[datetime] = None
    categoria_it: Optional[str] = None
    impacto: Optional[str] = None
    alerta_enviada: bool

    model_config = {"from_attributes": True}


class SLACreate(BaseModel):
    id_empresa: int
    nombre: str
    tiempo_respuesta_horas: int
    tiempo_resolucion_horas: int


class SLAOut(SLACreate):
    id_sla: int
    activo: bool

    model_config = {"from_attributes": True}
