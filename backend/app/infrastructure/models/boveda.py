from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Credencial(Base):
    """AES-256-GCM encrypted credential stored in the B2B vault."""

    __tablename__ = "credencial"

    id_credencial: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_empresa: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.id_cliente"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    usuario_acceso: Mapped[str | None] = mapped_column(String(200))
    password_cifrado: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256-GCM
    url: Mapped[str | None] = mapped_column(String(500))
    notas: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="credenciales")
