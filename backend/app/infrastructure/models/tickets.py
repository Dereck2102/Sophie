from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Interval,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PrioridadEnum(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class EstadoTicketEnum(str, enum.Enum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    ESPERANDO_CLIENTE = "esperando_cliente"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class TipoTicketEnum(str, enum.Enum):
    REPARACION = "reparacion"
    INCIDENCIA_IT = "incidencia_it"


class SLA(Base):
    __tablename__ = "sla"

    id_sla: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_empresa: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.id_cliente"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tiempo_respuesta_horas: Mapped[int] = mapped_column(Integer, nullable=False)
    tiempo_resolucion_horas: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True)

    empresa: Mapped["Empresa"] = relationship(back_populates="slas")
    incidencias: Mapped[list["IncidenciaIT"]] = relationship(back_populates="sla")


class Ticket(Base):
    __tablename__ = "ticket"

    id_ticket: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    tipo: Mapped[TipoTicketEnum] = mapped_column(Enum(TipoTicketEnum), nullable=False)
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente"), nullable=False
    )
    id_tecnico: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario")
    )
    prioridad: Mapped[PrioridadEnum] = mapped_column(
        Enum(PrioridadEnum), default=PrioridadEnum.MEDIA
    )
    estado: Mapped[EstadoTicketEnum] = mapped_column(
        Enum(EstadoTicketEnum), default=EstadoTicketEnum.ABIERTO
    )
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_inicio_trabajo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_fin_trabajo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cliente: Mapped["Cliente"] = relationship(back_populates="tickets")
    tecnico: Mapped["Usuario | None"] = relationship()
    reparacion: Mapped["ReparacionTaller | None"] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )
    incidencia_it: Mapped["IncidenciaIT | None"] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )


class ReparacionTaller(Base):
    __tablename__ = "reparacion_taller"

    id_ticket: Mapped[int] = mapped_column(
        Integer, ForeignKey("ticket.id_ticket", ondelete="CASCADE"), primary_key=True
    )
    equipo_descripcion: Mapped[str | None] = mapped_column(Text)
    numero_serie_equipo: Mapped[str | None] = mapped_column(String(100))
    diagnostico: Mapped[str | None] = mapped_column(Text)
    fotos_urls: Mapped[str | None] = mapped_column(Text)  # JSON array of URLs
    costo_reparacion: Mapped[float | None] = mapped_column(Numeric(12, 2))

    ticket: Mapped["Ticket"] = relationship(back_populates="reparacion")
    repuestos: Mapped[list["RepuestoUsado"]] = relationship(back_populates="reparacion")


class RepuestoUsado(Base):
    __tablename__ = "repuesto_usado"

    id_repuesto: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_ticket: Mapped[int] = mapped_column(
        Integer, ForeignKey("reparacion_taller.id_ticket", ondelete="CASCADE"), nullable=False
    )
    id_serie: Mapped[int | None] = mapped_column(Integer, ForeignKey("inventario_serie.id_serie"))
    id_producto: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventario.id_producto"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    reparacion: Mapped["ReparacionTaller"] = relationship(back_populates="repuestos")
    serie: Mapped["InventarioSerie | None"] = relationship()
    producto: Mapped["Inventario"] = relationship()


class IncidenciaIT(Base):
    __tablename__ = "incidencia_it"

    id_ticket: Mapped[int] = mapped_column(
        Integer, ForeignKey("ticket.id_ticket", ondelete="CASCADE"), primary_key=True
    )
    id_sla: Mapped[int | None] = mapped_column(Integer, ForeignKey("sla.id_sla"))
    fecha_limite_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_limite_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_primera_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    categoria_it: Mapped[str | None] = mapped_column(String(100))
    impacto: Mapped[str | None] = mapped_column(String(100))
    alerta_enviada: Mapped[bool] = mapped_column(default=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="incidencia_it")
    sla: Mapped["SLA | None"] = relationship(back_populates="incidencias")
