from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"

    id_configuracion: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    nombre_instancia: Mapped[str] = mapped_column(String(120), default="SOPHIE")
    nombre_empresa: Mapped[str] = mapped_column(String(200), default="Big Solutions")
    ruc_empresa: Mapped[str | None] = mapped_column(String(20))
    logo_empresa_url: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(80), default="America/Guayaquil")
    market: Mapped[str] = mapped_column(String(20), default="EC")
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    system_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=30)
    require_mfa_global: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_twofa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_channel_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_channel_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_channel_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_login_attempts: Mapped[int] = mapped_column(Integer, default=5)
    color_primario: Mapped[str | None] = mapped_column(String(20), default="#2563eb")
    color_secundario: Mapped[str | None] = mapped_column(String(20), default="#0f172a")
    reporte_footer: Mapped[str | None] = mapped_column(Text)
    iva_default_percent: Mapped[int] = mapped_column(Integer, default=15)
    descuento_default_percent: Mapped[int] = mapped_column(Integer, default=0)
    costo_hora_tecnica_default: Mapped[int] = mapped_column(Integer, default=25)
    costo_movilizacion_default: Mapped[int] = mapped_column(Integer, default=0)
    costo_software_default: Mapped[int] = mapped_column(Integer, default=0)
    costo_material_default: Mapped[int] = mapped_column(Integer, default=0)
    costo_mano_obra_default: Mapped[int] = mapped_column(Integer, default=0)
    fondo_caja_chica_mensual: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )