from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoProyectoEnum(str, enum.Enum):
    PROPUESTA = "propuesta"
    EN_PROGRESO = "en_progreso"
    PAUSADO = "pausado"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class Proyecto(Base):
    __tablename__ = "proyecto"

    id_proyecto: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("cliente.id_cliente"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[EstadoProyectoEnum] = mapped_column(
        Enum(EstadoProyectoEnum), default=EstadoProyectoEnum.PROPUESTA
    )
    presupuesto: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cliente: Mapped["Cliente"] = relationship()
    tareas: Mapped[list["Tarea"]] = relationship(
        back_populates="proyecto", cascade="all, delete-orphan"
    )
    miembros: Mapped[list["MiembroProyecto"]] = relationship(back_populates="proyecto")


class Tarea(Base):
    __tablename__ = "tarea"

    id_tarea: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_proyecto: Mapped[int] = mapped_column(
        Integer, ForeignKey("proyecto.id_proyecto", ondelete="CASCADE"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    horas_estimadas: Mapped[float | None] = mapped_column(Numeric(8, 2))
    horas_reales: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    proyecto: Mapped["Proyecto"] = relationship(back_populates="tareas")
    registros_tiempo: Mapped[list["RegistroTiempo"]] = relationship(back_populates="tarea")


class MiembroProyecto(Base):
    __tablename__ = "miembro_proyecto"

    id_miembro: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_proyecto: Mapped[int] = mapped_column(
        Integer, ForeignKey("proyecto.id_proyecto", ondelete="CASCADE"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )
    rol_en_proyecto: Mapped[str | None] = mapped_column(String(100))

    proyecto: Mapped["Proyecto"] = relationship(back_populates="miembros")
    usuario: Mapped["Usuario"] = relationship()


class RegistroTiempo(Base):
    __tablename__ = "registro_tiempo"

    id_registro: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_tarea: Mapped[int] = mapped_column(
        Integer, ForeignKey("tarea.id_tarea", ondelete="CASCADE"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )
    horas: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tarea: Mapped["Tarea"] = relationship(back_populates="registros_tiempo")
    usuario: Mapped["Usuario"] = relationship()
