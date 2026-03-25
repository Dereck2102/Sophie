"""Add subscription ownership and company branding

Revision ID: 002
Revises: 001
Create Date: 2026-03-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS branding_nombre VARCHAR(200)")
    op.execute("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS branding_logo_url VARCHAR(500)")

    op.execute("ALTER TABLE payment_transaction ADD COLUMN IF NOT EXISTS id_usuario_owner INTEGER")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_payment_transaction_id_usuario_owner'
            ) THEN
                ALTER TABLE payment_transaction
                ADD CONSTRAINT fk_payment_transaction_id_usuario_owner
                FOREIGN KEY (id_usuario_owner)
                REFERENCES usuario(id_usuario)
                ON DELETE SET NULL;
            END IF;
        END$$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_payment_transaction_id_usuario_owner ON payment_transaction (id_usuario_owner)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_subscription (
            id_usuario INTEGER PRIMARY KEY,
            plan_tier plantierenum NOT NULL DEFAULT 'starter',
            billing_cycle billingcycleenum NOT NULL DEFAULT 'monthly',
            status subscriptionstatusenum NOT NULL DEFAULT 'pending',
            price_usd NUMERIC(10,2) NOT NULL DEFAULT 0,
            currency VARCHAR(8) NOT NULL DEFAULT 'USD',
            features_json TEXT,
            custom_notes VARCHAR(800),
            updated_by_user_id INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_user_subscription_id_usuario FOREIGN KEY (id_usuario)
                REFERENCES usuario(id_usuario) ON DELETE CASCADE,
            CONSTRAINT fk_user_subscription_updated_by_user_id FOREIGN KEY (updated_by_user_id)
                REFERENCES usuario(id_usuario)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_subscription_updated_by ON user_subscription (updated_by_user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_subscription_updated_by")
    op.execute("DROP TABLE IF EXISTS user_subscription")

    op.execute("DROP INDEX IF EXISTS ix_payment_transaction_id_usuario_owner")
    op.execute("ALTER TABLE payment_transaction DROP CONSTRAINT IF EXISTS fk_payment_transaction_id_usuario_owner")
    op.execute("ALTER TABLE payment_transaction DROP COLUMN IF EXISTS id_usuario_owner")

    op.execute("ALTER TABLE empresa DROP COLUMN IF EXISTS branding_logo_url")
    op.execute("ALTER TABLE empresa DROP COLUMN IF EXISTS branding_nombre")
