"""Add new role values to rolenum enum

Revision ID: 001
Revises:
Create Date: 2026-03-17

Notes: PostgreSQL ALTER TYPE ... ADD VALUE IF NOT EXISTS must run outside
an explicit transaction. We open an AUTOCOMMIT connection for these DDL ops.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels = None
depends_on = None

_NEW_ROLES = [
    "admin",
    "jefe_tecnologias",
    "jefe_taller",
    "jefe_administrativo",
    "jefe_contable",
    "tecnico_taller",
    "agente_soporte_l1",
    "agente_soporte_l2",
    "desarrollador",
]


def upgrade() -> None:
    conn = op.get_bind()
    conn = conn.execution_options(isolation_level="AUTOCOMMIT")
    for role in _NEW_ROLES:
        conn.execute(sa.text(f"ALTER TYPE rolenum ADD VALUE IF NOT EXISTS '{role}'"))


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum values.
    # Downgrade is a no-op; manual intervention required if needed.
    pass
