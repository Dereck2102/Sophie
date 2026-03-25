"""Add usuario.id_empresa column

Revision ID: 004
Revises: 003
Create Date: 2026-03-24
"""
from __future__ import annotations

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS id_empresa INTEGER")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_usuario_id_empresa'
            ) THEN
                ALTER TABLE usuario
                ADD CONSTRAINT fk_usuario_id_empresa
                FOREIGN KEY (id_empresa)
                REFERENCES cliente(id_cliente)
                ON DELETE SET NULL;
            END IF;
        END$$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_usuario_id_empresa ON usuario (id_empresa)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_usuario_id_empresa")
    op.execute("ALTER TABLE usuario DROP CONSTRAINT IF EXISTS fk_usuario_id_empresa")
    op.execute("ALTER TABLE usuario DROP COLUMN IF EXISTS id_empresa")
