"""Add configuracion_empresa and configuracion_usuario tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primero, agregar columnas a las tablas existentes
    op.add_column('usuario', sa.Column('tipo_suscripcion', sa.String(length=20), nullable=True, server_default='corporativa'))
    op.add_column('usuario', sa.Column('es_admin_global', sa.Boolean(), nullable=True, server_default=sa.false()))
    op.add_column('empresa', sa.Column('branding_slogan', sa.String(length=255), nullable=True))
    
    # Crear tabla configuracion_empresa
    op.create_table(
        'configuracion_empresa',
        sa.Column('id_config', sa.Integer(), nullable=False),
        sa.Column('id_cliente', sa.Integer(), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('market', sa.String(length=50), nullable=True),
        sa.Column('require_mfa_global', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('session_timeout_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_login_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('color_primario', sa.String(length=7), nullable=True),
        sa.Column('color_secundario', sa.String(length=7), nullable=True),
        sa.Column('default_iva', sa.Numeric(precision=5, scale=2), nullable=False, server_default='21.0'),
        sa.Column('default_descuento', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('payphone_key', sa.String(length=255), nullable=True),
        sa.Column('payphone_secret', sa.String(length=255), nullable=True),
        sa.Column('stripe_key', sa.String(length=255), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['id_cliente'], ['cliente.id_cliente'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_config'),
        sa.UniqueConstraint('id_cliente'),
    )
    op.create_index(op.f('ix_configuracion_empresa_id_cliente'), 'configuracion_empresa', ['id_cliente'], unique=True)
    
    # Crear tabla configuracion_usuario
    op.create_table(
        'configuracion_usuario',
        sa.Column('id_config', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('preferencia_idioma', sa.String(length=10), nullable=False, server_default='es'),
        sa.Column('tema', sa.String(length=20), nullable=False, server_default='system'),
        sa.Column('notificaciones_email', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notificaciones_sms', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('timezone_personal', sa.String(length=50), nullable=True),
        sa.Column('reporte_footer', sa.Text(), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id_usuario'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_config'),
        sa.UniqueConstraint('id_usuario'),
    )
    op.create_index(op.f('ix_configuracion_usuario_id_usuario'), 'configuracion_usuario', ['id_usuario'], unique=True)
    
    # Agregar índices para tipo_suscripcion y es_admin_global
    op.create_index('idx_usuario_tipo_suscripcion', 'usuario', ['tipo_suscripcion'])
    op.create_index('idx_usuario_es_admin_global', 'usuario', ['es_admin_global'])


def downgrade() -> None:
    op.drop_index('idx_usuario_es_admin_global', table_name='usuario')
    op.drop_index('idx_usuario_tipo_suscripcion', table_name='usuario')
    op.drop_index(op.f('ix_configuracion_usuario_id_usuario'), table_name='configuracion_usuario')
    op.drop_table('configuracion_usuario')
    op.drop_index(op.f('ix_configuracion_empresa_id_cliente'), table_name='configuracion_empresa')
    op.drop_table('configuracion_empresa')
    op.drop_column('empresa', 'branding_slogan')
    op.drop_column('usuario', 'es_admin_global')
    op.drop_column('usuario', 'tipo_suscripcion')
