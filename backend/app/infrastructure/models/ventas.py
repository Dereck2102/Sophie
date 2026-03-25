from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoCotizacionEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADA = "enviada"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    FACTURADA = "facturada"


class EstadoVentaEnum(str, enum.Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    FACTURADA = "facturada"
    ANULADA = "anulada"


class Cotizacion(Base):
    __tablename__ = "cotizacion"

    id_cotizacion: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cliente.id_cliente", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente"), nullable=False
    )
    id_vendedor: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )
    id_proyecto: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proyecto.id_proyecto", ondelete="SET NULL")
    )
    estado: Mapped[EstadoCotizacionEnum] = mapped_column(
        Enum(EstadoCotizacionEnum), default=EstadoCotizacionEnum.BORRADOR
    )
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    impuesto: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    costo_mano_obra: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    costo_movilizacion: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    costo_software: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    horas_soporte: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    tarifa_hora_soporte: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notas: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_vencimiento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cliente: Mapped["Cliente"] = relationship(
        back_populates="cotizaciones", foreign_keys=[id_cliente]
    )
    vendedor: Mapped["Usuario"] = relationship()
    proyecto: Mapped["Proyecto | None"] = relationship("Proyecto")
    detalles: Mapped[list["DetalleCotizacion"]] = relationship(
        back_populates="cotizacion", cascade="all, delete-orphan"
    )
    venta: Mapped["Venta | None"] = relationship(back_populates="cotizacion", uselist=False)


class DetalleCotizacion(Base):
    __tablename__ = "detalle_cotizacion"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cotizacion: Mapped[int] = mapped_column(
        Integer, ForeignKey("cotizacion.id_cotizacion", ondelete="CASCADE"), nullable=False
    )
    id_producto: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventario.id_producto", ondelete="CASCADE"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    descuento: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    cotizacion: Mapped["Cotizacion"] = relationship(back_populates="detalles")
    producto: Mapped["Inventario"] = relationship(back_populates="detalle_cotizacion")


class Venta(Base):
    __tablename__ = "venta"

    id_venta: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cotizacion: Mapped[int] = mapped_column(
        Integer, ForeignKey("cotizacion.id_cotizacion"), unique=True, nullable=False
    )
    numero_factura: Mapped[str | None] = mapped_column(String(30), unique=True)
    estado: Mapped[EstadoVentaEnum] = mapped_column(
        Enum(EstadoVentaEnum), default=EstadoVentaEnum.PENDIENTE
    )
    fecha_venta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_factura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cotizacion: Mapped["Cotizacion"] = relationship(back_populates="venta")
