from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LogAuditoria(Base):
    """Append-only audit log. UPDATE/DELETE are prohibited at application level."""

    __tablename__ = "log_auditoria"

    id_log: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.id_cliente", ondelete="SET NULL"))
    id_usuario: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuario.id_usuario"))
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    accion_tipo: Mapped[str | None] = mapped_column(String(40))
    accion_nombre: Mapped[str | None] = mapped_column(String(140))
    modulo: Mapped[str] = mapped_column(String(100), nullable=False)
    metodo_http: Mapped[str | None] = mapped_column(String(16))
    ruta: Mapped[str | None] = mapped_column(String(300))
    ip_origen: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    pais_origen: Mapped[str | None] = mapped_column(String(120))
    ciudad_origen: Mapped[str | None] = mapped_column(String(120))
    ubicacion_aprox: Mapped[str | None] = mapped_column(String(200))
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario | None"] = relationship(back_populates="logs")


class EventoCliente(Base):
    """Client timeline events - populated via SQLAlchemy hooks."""

    __tablename__ = "evento_cliente"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente", ondelete="CASCADE"), nullable=False
    )
    tipo_evento: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="eventos")
