"""Add Payflex columns to orders table.

Revision ID: 002_payflex
Revises: (auto)
"""
from alembic import op
import sqlalchemy as sa

revision = '002_payflex'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('payment_provider', sa.String(20), nullable=True))
    op.add_column('orders', sa.Column('payflex_order_id', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('payflex_token', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('payflex_payment_id', sa.String(100), nullable=True))

    op.create_index('ix_orders_payflex_order_id', 'orders', ['payflex_order_id'])


def downgrade() -> None:
    op.drop_index('ix_orders_payflex_order_id', table_name='orders')
    op.drop_column('orders', 'payflex_payment_id')
    op.drop_column('orders', 'payflex_token')
    op.drop_column('orders', 'payflex_order_id')
    op.drop_column('orders', 'payment_provider')
