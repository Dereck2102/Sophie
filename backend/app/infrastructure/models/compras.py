from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoOrdenEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADA = "enviada"
    RECIBIDA_PARCIAL = "recibida_parcial"
    RECIBIDA_TOTAL = "recibida_total"
    CANCELADA = "cancelada"


class OrdenCompra(Base):
    __tablename__ = "orden_compra"

    id_orden: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    id_proveedor: Mapped[int] = mapped_column(
        Integer, ForeignKey("proveedor.id_proveedor"), nullable=False
    )
    id_comprador: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )
    estado: Mapped[EstadoOrdenEnum] = mapped_column(
        Enum(EstadoOrdenEnum), default=EstadoOrdenEnum.BORRADOR
    )
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notas: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_entrega_esperada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    proveedor: Mapped["Proveedor"] = relationship(back_populates="ordenes_compra")
    comprador: Mapped["Usuario"] = relationship()
    detalles: Mapped[list["DetalleOrdenCompra"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


class DetalleOrdenCompra(Base):
    __tablename__ = "detalle_orden_compra"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_orden: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_compra.id_orden", ondelete="CASCADE"), nullable=False
    )
    id_producto: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventario.id_producto", ondelete="CASCADE"), nullable=False
    )
    cantidad_pedida: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_recibida: Mapped[int] = mapped_column(Integer, default=0)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    orden: Mapped["OrdenCompra"] = relationship(back_populates="detalles")
    producto: Mapped["Inventario"] = relationship(back_populates="detalle_orden")
