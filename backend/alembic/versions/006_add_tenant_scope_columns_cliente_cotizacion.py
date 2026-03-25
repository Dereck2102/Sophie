"""Add tenant scope columns for cliente and cotizacion

Revision ID: 006
Revises: 005
Create Date: 2026-03-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: str | None = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cliente", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_cliente_tenant_id", "cliente", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_cliente_tenant_id",
        "cliente",
        "cliente",
        ["tenant_id"],
        ["id_cliente"],
        ondelete="SET NULL",
    )

    op.add_column("cotizacion", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_cotizacion_tenant_id", "cotizacion", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_cotizacion_tenant_id",
        "cotizacion",
        "cliente",
        ["tenant_id"],
        ["id_cliente"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE cliente c
        SET tenant_id = c.id_cliente
        WHERE c.tenant_id IS NULL
          AND EXISTS (
            SELECT 1
            FROM empresa e
            WHERE e.id_cliente = c.id_cliente
          );
        """
    )

    op.execute(
        """
        UPDATE cotizacion co
        SET tenant_id = u.id_cliente
        FROM usuario u
        WHERE co.tenant_id IS NULL
          AND co.id_vendedor = u.id_usuario
          AND u.id_cliente IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_cotizacion_tenant_id", "cotizacion", type_="foreignkey")
    op.drop_index("ix_cotizacion_tenant_id", table_name="cotizacion")
    op.drop_column("cotizacion", "tenant_id")

    op.drop_constraint("fk_cliente_tenant_id", "cliente", type_="foreignkey")
    op.drop_index("ix_cliente_tenant_id", table_name="cliente")
    op.drop_column("cliente", "tenant_id")
