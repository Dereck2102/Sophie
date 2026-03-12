from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.infrastructure.models.proyectos import EstadoProyectoEnum


class ProyectoCreate(BaseModel):
    id_cliente: int
    nombre: str
    descripcion: Optional[str] = None
    estado: EstadoProyectoEnum = EstadoProyectoEnum.PROPUESTA
    presupuesto: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[EstadoProyectoEnum] = None
    presupuesto: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


class ProyectoOut(BaseModel):
    id_proyecto: int
    id_cliente: int
    nombre: str
    descripcion: Optional[str] = None
    estado: EstadoProyectoEnum
    presupuesto: Optional[float] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class TareaCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    estado: str = "pendiente"
    prioridad: str = "media"
    id_asignado: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    etiquetas: Optional[str] = None  # JSON array
    horas_estimadas: Optional[float] = None


class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    id_asignado: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    etiquetas: Optional[str] = None
    horas_estimadas: Optional[float] = None
    horas_reales: Optional[float] = None


class TareaOut(BaseModel):
    id_tarea: int
    id_proyecto: int
    titulo: str
    descripcion: Optional[str] = None
    estado: str
    prioridad: str
    id_asignado: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    etiquetas: Optional[str] = None
    horas_estimadas: Optional[float] = None
    horas_reales: float
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class RegistroTiempoCreate(BaseModel):
    id_tarea: int
    horas: float
    descripcion: Optional[str] = None


class RegistroTiempoOut(BaseModel):
    id_registro: int
    id_tarea: int
    id_usuario: int
    horas: float
    descripcion: Optional[str] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class MiembroCreate(BaseModel):
    id_usuario: int
    rol_en_proyecto: Optional[str] = None


class MiembroOut(BaseModel):
    id_miembro: int
    id_proyecto: int
    id_usuario: int
    rol_en_proyecto: Optional[str] = None

    model_config = {"from_attributes": True}
