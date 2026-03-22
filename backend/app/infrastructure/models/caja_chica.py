from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TipoMovimientoCajaEnum(str, enum.Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"
    AJUSTE = "ajuste"


class MovimientoCajaChica(Base):
    __tablename__ = "movimiento_caja_chica"

    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.id_cliente", ondelete="SET NULL"), index=True)
    tipo: Mapped[TipoMovimientoCajaEnum] = mapped_column(Enum(TipoMovimientoCajaEnum), nullable=False)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100))
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    responsable: Mapped[str | None] = mapped_column(String(150))
    observacion: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
