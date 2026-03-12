from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.infrastructure.models.inventario import CategoriaInventarioEnum, EstadoSerieEnum


class ProveedorCreate(BaseModel):
    razon_social: str
    ruc: Optional[str] = None
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


class ProveedorOut(ProveedorCreate):
    id_proveedor: int
    activo: bool

    model_config = {"from_attributes": True}


class InventarioCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria: CategoriaInventarioEnum
    requiere_serie: bool = False
    stock_actual: int = 0
    stock_minimo: int = 0
    precio_venta: float
    costo_adquisicion: float = 0
    id_proveedor: Optional[int] = None


class InventarioUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[CategoriaInventarioEnum] = None
    requiere_serie: Optional[bool] = None
    stock_actual: Optional[int] = None
    precio_venta: Optional[float] = None
    costo_adquisicion: Optional[float] = None
    stock_minimo: Optional[int] = None
    id_proveedor: Optional[int] = None


class InventarioOut(BaseModel):
    id_producto: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria: CategoriaInventarioEnum
    requiere_serie: bool
    stock_actual: int
    stock_minimo: int
    precio_venta: float
    costo_adquisicion: float
    id_proveedor: Optional[int] = None

    model_config = {"from_attributes": True}


class InventarioOutVendedor(BaseModel):
    """Redacted view for vendedor role - no cost or supplier info."""

    id_producto: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria: CategoriaInventarioEnum
    stock_actual: int
    precio_venta: float

    model_config = {"from_attributes": True}


class SerieCreate(BaseModel):
    id_producto: int
    numero_serie: str
    notas: Optional[str] = None


class SerieUpdate(BaseModel):
    estado: EstadoSerieEnum
    notas: Optional[str] = None


class SerieOut(BaseModel):
    id_serie: int
    id_producto: int
    numero_serie: str
    estado: EstadoSerieEnum
    fecha_ingreso: datetime

    model_config = {"from_attributes": True}
