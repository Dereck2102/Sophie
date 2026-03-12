from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RolEnum(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    EJECUTIVO = "ejecutivo"
    ADMINISTRATIVO_CONTABLE = "administrativo_contable"
    VENDEDOR = "vendedor"
    TECNICO_TALLER = "tecnico_taller"
    TECNICO_IT = "tecnico_it"
    COMPRADOR = "comprador"
    DESARROLLADOR = "desarrollador"
    CONSULTOR_SENIOR = "consultor_senior"


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolEnum] = mapped_column(Enum(RolEnum), nullable=False)
    nombre_completo: Mapped[str | None] = mapped_column(String(150))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    force_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    foto_perfil_url: Mapped[str | None] = mapped_column(Text)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verificacion_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True
    )
    email_verificacion_expira: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permisos_json: Mapped[str | None] = mapped_column(Text)
    vistas_json: Mapped[str | None] = mapped_column(Text)
    herramientas_json: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    logs: Mapped[list["LogAuditoria"]] = relationship(back_populates="usuario")
