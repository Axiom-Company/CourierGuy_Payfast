"""Migrate from users table to Supabase-managed profiles table.

The profiles table is created by Supabase SQL (with FK to auth.users and trigger).
This migration drops the old users table and re-points FKs to profiles.

RUN supabase_profiles_setup.sql in Supabase SQL Editor BEFORE this migration.

Revision ID: 004_profiles
Revises: 003_exchange_rates
"""
from alembic import op
import sqlalchemy as sa

revision = '004_profiles'
down_revision = '003_exchange_rates'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t)"
        ),
        {"t": table_name},
    )
    return result.scalar()


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :t AND constraint_name = :c)"
        ),
        {"t": table_name, "c": constraint_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Drop FK constraints that reference the old users table (only if they exist)
    if _constraint_exists('orders', 'orders_customer_id_fkey'):
        op.drop_constraint('orders_customer_id_fkey', 'orders', type_='foreignkey')
    if _constraint_exists('cart_items', 'cart_items_user_id_fkey'):
        op.drop_constraint('cart_items_user_id_fkey', 'cart_items', type_='foreignkey')

    # Drop the old users table (only if it exists)
    if _table_exists('users'):
        op.drop_table('users')

    # Re-create FK constraints pointing to profiles (only if both tables exist)
    if _table_exists('orders') and _table_exists('profiles'):
        op.create_foreign_key(
            'orders_customer_id_fkey', 'orders', 'profiles',
            ['customer_id'], ['id'],
        )
    if _table_exists('cart_items') and _table_exists('profiles'):
        op.create_foreign_key(
            'cart_items_user_id_fkey', 'cart_items', 'profiles',
            ['user_id'], ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    if _constraint_exists('orders', 'orders_customer_id_fkey'):
        op.drop_constraint('orders_customer_id_fkey', 'orders', type_='foreignkey')
    if _constraint_exists('cart_items', 'cart_items_user_id_fkey'):
        op.drop_constraint('cart_items_user_id_fkey', 'cart_items', type_='foreignkey')

    import sqlalchemy as sa
    if not _table_exists('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('email', sa.String(255), unique=True, nullable=False),
            sa.Column('password_hash', sa.String(255), nullable=False),
            sa.Column('full_name', sa.String(255), nullable=False),
            sa.Column('phone', sa.String(20), nullable=True),
            sa.Column('role', sa.String(20), nullable=False, server_default='customer'),
            sa.Column('address_line1', sa.String(255), nullable=True),
            sa.Column('address_line2', sa.String(255), nullable=True),
            sa.Column('city', sa.String(100), nullable=True),
            sa.Column('province', sa.String(100), nullable=True),
            sa.Column('postal_code', sa.String(10), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )

    if _table_exists('orders') and _table_exists('users'):
        op.create_foreign_key(
            'orders_customer_id_fkey', 'orders', 'users',
            ['customer_id'], ['id'],
        )
    if _table_exists('cart_items') and _table_exists('users'):
        op.create_foreign_key(
            'cart_items_user_id_fkey', 'cart_items', 'users',
            ['user_id'], ['id'],
            ondelete='CASCADE',
        )
