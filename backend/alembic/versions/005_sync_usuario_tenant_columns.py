"""Sync usuario tenant columns id_cliente/id_empresa

Revision ID: 005
Revises: 004
Create Date: 2026-03-24
"""
from __future__ import annotations

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE usuario
        SET id_empresa = id_cliente
        WHERE id_cliente IS NOT NULL
          AND id_empresa IS NULL;
        """
    )
    op.execute(
        """
        UPDATE usuario
        SET id_cliente = id_empresa
        WHERE id_cliente IS NULL
          AND id_empresa IS NOT NULL;
        """
    )
    op.execute("ALTER TABLE usuario DROP CONSTRAINT IF EXISTS ck_usuario_tenant_sync")
    op.execute(
        """
        ALTER TABLE usuario
        ADD CONSTRAINT ck_usuario_tenant_sync
        CHECK (
            (id_cliente IS NULL AND id_empresa IS NULL)
            OR (id_cliente IS NOT NULL AND id_empresa = id_cliente)
        ) NOT VALID;
        """
    )
    op.execute("ALTER TABLE usuario VALIDATE CONSTRAINT ck_usuario_tenant_sync")


def downgrade() -> None:
    op.execute("ALTER TABLE usuario DROP CONSTRAINT IF EXISTS ck_usuario_tenant_sync")
