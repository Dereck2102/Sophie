from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


_DEVELOPMENT_SCHEMA_PATCHES = (
    "ALTER TYPE rolenum ADD VALUE IF NOT EXISTS 'TECNICO'",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_inicio_trabajo TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_fin_trabajo TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_cierre TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS id_proyecto INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_ticket_id_proyecto ON ticket (id_proyecto)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS equipo_descripcion TEXT",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS marca_equipo VARCHAR(100)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS modelo_equipo VARCHAR(100)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS numero_serie_equipo VARCHAR(100)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS accesorios_recibidos TEXT",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS diagnostico TEXT",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS fotos_urls TEXT",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS costo_reparacion NUMERIC(12, 2)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS token_seguimiento VARCHAR(64)",
    "ALTER TABLE IF EXISTS reparacion_taller ADD COLUMN IF NOT EXISTS email_cliente VARCHAR(255)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_reparacion_taller_token_seguimiento ON reparacion_taller (token_seguimiento)",
    "ALTER TABLE IF EXISTS incidencia_it ADD COLUMN IF NOT EXISTS fecha_primera_respuesta TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS incidencia_it ADD COLUMN IF NOT EXISTS categoria_it VARCHAR(100)",
    "ALTER TABLE IF EXISTS incidencia_it ADD COLUMN IF NOT EXISTS impacto VARCHAR(100)",
    "ALTER TABLE IF EXISTS incidencia_it ADD COLUMN IF NOT EXISTS alerta_enviada BOOLEAN DEFAULT FALSE",
    "ALTER TABLE IF EXISTS inventario ADD COLUMN IF NOT EXISTS costo_adquisicion NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS empresa ADD COLUMN IF NOT EXISTS direccion VARCHAR(300)",
    "ALTER TABLE IF EXISTS empresa ADD COLUMN IF NOT EXISTS sector VARCHAR(100)",
    "ALTER TABLE IF EXISTS cliente_b2c ADD COLUMN IF NOT EXISTS direccion VARCHAR(300)",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS fecha_vencimiento TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS id_proyecto INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_cotizacion_id_proyecto ON cotizacion (id_proyecto)",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS costo_mano_obra NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS costo_movilizacion NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS costo_software NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS horas_soporte NUMERIC(8, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS cotizacion ADD COLUMN IF NOT EXISTS tarifa_hora_soporte NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS venta ADD COLUMN IF NOT EXISTS fecha_factura TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS foto_perfil_url TEXT",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS force_mfa BOOLEAN DEFAULT FALSE",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN DEFAULT FALSE",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS email_verificacion_token VARCHAR(128)",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS email_verificacion_expira TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS permisos_json TEXT",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS vistas_json TEXT",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS herramientas_json TEXT",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS id_cliente INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_usuario_id_cliente ON usuario (id_cliente)",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS telefono_recuperacion VARCHAR(30)",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS telefono_verificado BOOLEAN DEFAULT FALSE",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS recovery_codes_json TEXT",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS password_reset_token_hash VARCHAR(128)",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS password_reset_expira TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS password_reset_intentos INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS mfa_email_code_hash VARCHAR(128)",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS mfa_email_code_expira TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS mfa_email_code_intentos INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS refresh_token_version INTEGER DEFAULT 1",
    "ALTER TABLE IF EXISTS usuario ADD COLUMN IF NOT EXISTS ultima_rotacion_password TIMESTAMPTZ",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuario_email_verificacion_token ON usuario (email_verificacion_token)",
    "CREATE INDEX IF NOT EXISTS ix_usuario_password_reset_token_hash ON usuario (password_reset_token_hash)",
    "CREATE INDEX IF NOT EXISTS ix_usuario_mfa_email_code_hash ON usuario (mfa_email_code_hash)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_telefono_recuperacion ON usuario (telefono_recuperacion)",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS auth_twofa_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS auth_channel_email_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS auth_channel_sms_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS auth_channel_app_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS iva_default_percent INTEGER DEFAULT 15",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS descuento_default_percent INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS costo_hora_tecnica_default INTEGER DEFAULT 25",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS costo_movilizacion_default INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS costo_software_default INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS costo_material_default INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS costo_mano_obra_default INTEGER DEFAULT 0",
    "ALTER TABLE IF EXISTS configuracion_sistema ADD COLUMN IF NOT EXISTS fondo_caja_chica_mensual NUMERIC(12, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS prioridad VARCHAR(20) DEFAULT 'media'",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS id_asignado INTEGER",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS fecha_vencimiento TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS etiquetas TEXT",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS horas_estimadas NUMERIC(8, 2)",
    "ALTER TABLE IF EXISTS tarea ADD COLUMN IF NOT EXISTS horas_reales NUMERIC(8, 2) DEFAULT 0",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS id_cliente INTEGER",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS accion_tipo VARCHAR(40)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS accion_nombre VARCHAR(140)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS metodo_http VARCHAR(16)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS ruta VARCHAR(300)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS user_agent VARCHAR(300)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS pais_origen VARCHAR(120)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS ciudad_origen VARCHAR(120)",
    "ALTER TABLE IF EXISTS log_auditoria ADD COLUMN IF NOT EXISTS ubicacion_aprox VARCHAR(200)",
    "CREATE INDEX IF NOT EXISTS ix_log_auditoria_id_cliente ON log_auditoria (id_cliente)",
    "CREATE INDEX IF NOT EXISTS ix_log_auditoria_fecha ON log_auditoria (fecha)",
    "CREATE INDEX IF NOT EXISTS ix_log_auditoria_id_usuario ON log_auditoria (id_usuario)",
    "CREATE INDEX IF NOT EXISTS ix_log_auditoria_accion_tipo ON log_auditoria (accion_tipo)",
    "CREATE INDEX IF NOT EXISTS ix_log_auditoria_modulo ON log_auditoria (modulo)",
)


async def ensure_development_schema() -> None:
    """Patch legacy development databases that predate newer model columns.

    This project boots with `create_all()` in development, but existing Docker volumes
    keep old tables unchanged. These idempotent statements keep the local schema usable
    until proper Alembic migrations are added.
    """

    async with engine.begin() as conn:
        for statement in _DEVELOPMENT_SCHEMA_PATCHES:
            await conn.execute(text(statement))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
