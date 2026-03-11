from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.infrastructure.models.cliente import EstadoClienteEnum, TipoClienteEnum


class EmpresaBase(BaseModel):
    razon_social: str
    ruc: str
    contacto_principal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    sector: Optional[str] = None


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = None
    contacto_principal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    sector: Optional[str] = None


class EmpresaOut(EmpresaBase):
    id_cliente: int

    model_config = {"from_attributes": True}


class ClienteB2CBase(BaseModel):
    nombre_completo: str
    documento_identidad: str
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None


class ClienteB2CCreate(ClienteB2CBase):
    pass


class ClienteB2CUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None


class ClienteB2COut(ClienteB2CBase):
    id_cliente: int

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    tipo_cliente: TipoClienteEnum
    estado: EstadoClienteEnum = EstadoClienteEnum.ACTIVO
    empresa: Optional[EmpresaCreate] = None
    cliente_b2c: Optional[ClienteB2CCreate] = None


class ClienteUpdate(BaseModel):
    estado: Optional[EstadoClienteEnum] = None
    empresa: Optional[EmpresaUpdate] = None
    cliente_b2c: Optional[ClienteB2CUpdate] = None


class ClienteOut(BaseModel):
    id_cliente: int
    tipo_cliente: TipoClienteEnum
    fecha_registro: date
    estado: EstadoClienteEnum
    empresa: Optional[EmpresaOut] = None
    cliente_b2c: Optional[ClienteB2COut] = None

    model_config = {"from_attributes": True}


class EventoClienteOut(BaseModel):
    id_evento: int
    tipo_evento: str
    descripcion: str
    fecha: datetime

    model_config = {"from_attributes": True}
