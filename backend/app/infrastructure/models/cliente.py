from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
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
    tenant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cliente.id_cliente", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
    configuracion_empresa: Mapped["ConfiguracionEmpresa | None"] = relationship(
        back_populates="cliente", uselist=False, cascade="all, delete-orphan"
    )
    cotizaciones: Mapped[list["Cotizacion"]] = relationship(
        back_populates="cliente", foreign_keys="Cotizacion.id_cliente"
    )
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="cliente")
    eventos: Mapped[list["EventoCliente"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )


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
    branding_nombre: Mapped[str | None] = mapped_column(String(200))
    branding_logo_url: Mapped[str | None] = mapped_column(String(500))

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


class ConfiguracionEmpresa(Base):
    """Configuración específica de cada empresa (B2B)"""
    __tablename__ = "configuracion_empresa"

    id_config: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente", ondelete="CASCADE"), unique=True, index=True
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    market: Mapped[str | None] = mapped_column(String(50))
    require_mfa_global: Mapped[bool] = mapped_column(default=False)
    session_timeout_minutes: Mapped[int] = mapped_column(default=30)
    max_login_attempts: Mapped[int] = mapped_column(default=5)
    color_primario: Mapped[str | None] = mapped_column(String(7))
    color_secundario: Mapped[str | None] = mapped_column(String(7))
    default_iva: Mapped[float] = mapped_column(default=21.0)
    default_descuento: Mapped[float] = mapped_column(default=0.0)
    payphone_key: Mapped[str | None] = mapped_column(String(255))
    payphone_secret: Mapped[str | None] = mapped_column(String(255))
    stripe_key: Mapped[str | None] = mapped_column(String(255))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="configuracion_empresa")


class ConfiguracionUsuario(Base):
    """Configuración personal de cada usuario (preferencias)"""
    __tablename__ = "configuracion_usuario"

    id_config: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_usuario: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"), unique=True, index=True
    )
    preferencia_idioma: Mapped[str] = mapped_column(String(10), default="es")
    tema: Mapped[str] = mapped_column(String(20), default="system")
    notificaciones_email: Mapped[bool] = mapped_column(default=True)
    notificaciones_sms: Mapped[bool] = mapped_column(default=False)
    timezone_personal: Mapped[str | None] = mapped_column(String(50))
    reporte_footer: Mapped[str | None] = mapped_column(Text)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="configuracion_usuario")
