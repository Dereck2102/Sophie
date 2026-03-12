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
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_inicio_trabajo TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_fin_trabajo TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS fecha_cierre TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS ticket ADD COLUMN IF NOT EXISTS id_proyecto INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_ticket_id_proyecto ON ticket (id_proyecto)",
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
    "ALTER TABLE IF EXISTS venta ADD COLUMN IF NOT EXISTS fecha_factura TIMESTAMPTZ",
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
