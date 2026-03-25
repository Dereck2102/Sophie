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
    """Roles válidos en SOPHIE con permisos granulares adicionales."""
    SUPERADMIN = "superadmin"           # Acceso total + administración del sistema
    ADMIN = "admin"                     # Administrador (maestro o ERP según tenant)
    AGENTE_SOPORTE = "agente_soporte"   # Soporte ERP
    VENTAS = "ventas"                   # Ventas ERP
    CONTABLE = "contable"               # Contable ERP
    RRHH = "rrhh"                       # Recursos humanos ERP
    BODEGA = "bodega"                   # Bodega/inventario ERP

    # Legacy roles kept for backward compatibility with existing data.
    JEFE_TECNOLOGIAS = "jefe_tecnologias"   # Jefe de departamento de tecnología
    JEFE_TALLER = "jefe_taller"         # Jefe de departamento de taller
    JEFE_ADMINISTRATIVO = "jefe_administrativo"  # Jefe de área administrativa
    JEFE_CONTABLE = "jefe_contable"     # Jefe de contabilidad
    EJECUTIVO = "ejecutivo"             # Jefe de área / supervisión general
    ADMINISTRATIVO_CONTABLE = "administrativo_contable"  # Gestión financiera + compras
    TECNICO = "tecnico"                 # Técnico (propio de taller, tickets propios)
    TECNICO_TALLER = "tecnico_taller"   # Técnico especialista de taller
    AGENTE_SOPORTE_L1 = "agente_soporte_l1"  # Agente de soporte nivel 1
    AGENTE_SOPORTE_L2 = "agente_soporte_l2"  # Agente de soporte nivel 2
    DESARROLLADOR = "desarrollador"     # Desarrollador de software


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_cliente: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.id_cliente", ondelete="SET NULL"))
    id_empresa: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.id_cliente", ondelete="SET NULL"))
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
    telefono_recuperacion: Mapped[str | None] = mapped_column(String(30))
    telefono_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_codes_json: Mapped[str | None] = mapped_column(Text)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    password_reset_expira: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_reset_intentos: Mapped[int] = mapped_column(Integer, default=0)
    mfa_email_code_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    mfa_email_code_expira: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_email_code_intentos: Mapped[int] = mapped_column(Integer, default=0)
    refresh_token_version: Mapped[int] = mapped_column(Integer, default=1)
    ultima_rotacion_password: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permisos_json: Mapped[str | None] = mapped_column(Text)
    vistas_json: Mapped[str | None] = mapped_column(Text)
    herramientas_json: Mapped[str | None] = mapped_column(Text)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(String(64))
    last_login_user_agent: Mapped[str | None] = mapped_column(String(300))
    # Nuevas columnas para suscripción dual B2B/B2C
    tipo_suscripcion: Mapped[str] = mapped_column(String(20), default="corporativa", index=True)
    es_admin_global: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    logs: Mapped[list["LogAuditoria"]] = relationship(back_populates="usuario")
    configuracion_usuario: Mapped["ConfiguracionUsuario | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
