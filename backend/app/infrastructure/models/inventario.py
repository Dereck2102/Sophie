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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CategoriaInventarioEnum(str, enum.Enum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ACCESORIO = "accesorio"
    REPUESTO = "repuesto"
    LICENCIA = "licencia"


class EstadoSerieEnum(str, enum.Enum):
    DISPONIBLE = "disponible"
    VENDIDO = "vendido"
    EN_REPARACION = "en_reparacion"
    BAJA = "baja"


class Proveedor(Base):
    __tablename__ = "proveedor"

    id_proveedor: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    ruc: Mapped[str | None] = mapped_column(String(20), unique=True)
    contacto: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(default=True)

    productos: Mapped[list["Inventario"]] = relationship(back_populates="proveedor")
    ordenes_compra: Mapped[list["OrdenCompra"]] = relationship(back_populates="proveedor")


class Inventario(Base):
    __tablename__ = "inventario"

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[CategoriaInventarioEnum] = mapped_column(
        Enum(CategoriaInventarioEnum), nullable=False
    )
    requiere_serie: Mapped[bool] = mapped_column(default=False)
    stock_actual: Mapped[int] = mapped_column(Integer, default=0)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=0)
    precio_venta: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    costo_adquisicion: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    id_proveedor: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proveedor.id_proveedor")
    )

    proveedor: Mapped["Proveedor | None"] = relationship(back_populates="productos")
    series: Mapped[list["InventarioSerie"]] = relationship(back_populates="producto")
    detalle_cotizacion: Mapped[list["DetalleCotizacion"]] = relationship(
        back_populates="producto"
    )
    detalle_orden: Mapped[list["DetalleOrdenCompra"]] = relationship(back_populates="producto")


class InventarioSerie(Base):
    __tablename__ = "inventario_serie"
    __table_args__ = (UniqueConstraint("numero_serie"),)

    id_serie: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_producto: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventario.id_producto"), nullable=False
    )
    numero_serie: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    estado: Mapped[EstadoSerieEnum] = mapped_column(
        Enum(EstadoSerieEnum), default=EstadoSerieEnum.DISPONIBLE
    )
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notas: Mapped[str | None] = mapped_column(Text)

    producto: Mapped["Inventario"] = relationship(back_populates="series")
