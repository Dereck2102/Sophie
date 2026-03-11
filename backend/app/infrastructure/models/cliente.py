from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoClienteEnum(str, enum.Enum):
    B2B = "B2B"
    B2C = "B2C"


class EstadoClienteEnum(str, enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    PROSPECTO = "prospecto"


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tipo_cliente: Mapped[TipoClienteEnum] = mapped_column(Enum(TipoClienteEnum), nullable=False)
    fecha_registro: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    estado: Mapped[EstadoClienteEnum] = mapped_column(
        Enum(EstadoClienteEnum), default=EstadoClienteEnum.ACTIVO
    )

    empresa: Mapped["Empresa | None"] = relationship(
        back_populates="cliente", uselist=False, cascade="all, delete-orphan"
    )
    cliente_b2c: Mapped["ClienteB2C | None"] = relationship(
        back_populates="cliente", uselist=False, cascade="all, delete-orphan"
    )
    cotizaciones: Mapped[list["Cotizacion"]] = relationship(back_populates="cliente")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="cliente")
    eventos: Mapped[list["EventoCliente"]] = relationship(back_populates="cliente")


class Empresa(Base):
    __tablename__ = "empresa"

    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente", ondelete="CASCADE"), primary_key=True
    )
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    ruc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    contacto_principal: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(300))
    sector: Mapped[str | None] = mapped_column(String(100))

    cliente: Mapped["Cliente"] = relationship(back_populates="empresa")
    credenciales: Mapped[list["Credencial"]] = relationship(back_populates="empresa")
    slas: Mapped[list["SLA"]] = relationship(back_populates="empresa")


class ClienteB2C(Base):
    __tablename__ = "cliente_b2c"

    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente", ondelete="CASCADE"), primary_key=True
    )
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    documento_identidad: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(300))

    cliente: Mapped["Cliente"] = relationship(back_populates="cliente_b2c")
