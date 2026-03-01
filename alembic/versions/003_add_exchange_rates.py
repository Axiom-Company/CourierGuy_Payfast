"""Add exchange_rates table for USD/ZAR rate caching.

Revision ID: 003_exchange_rates
Revises: 002_payflex
"""
from alembic import op
import sqlalchemy as sa

revision = '003_exchange_rates'
down_revision = '002_payflex'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('from_currency', sa.String(3), server_default='USD', nullable=False),
        sa.Column('to_currency', sa.String(3), server_default='ZAR', nullable=False),
        sa.Column('rate', sa.Numeric(10, 4), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_exchange_rates_fetched_at', 'exchange_rates', ['fetched_at'])


def downgrade() -> None:
    op.drop_index('ix_exchange_rates_fetched_at', table_name='exchange_rates')
    op.drop_table('exchange_rates')
