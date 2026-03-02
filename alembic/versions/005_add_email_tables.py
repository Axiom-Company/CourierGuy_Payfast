"""Add email_logs and notification_preferences tables.

Revision ID: 005_email_tables
Revises: 004_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "005_email_tables"
down_revision = "004_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_email", sa.String(255), nullable=False, index=True),
        sa.Column("email_type", sa.String(50), nullable=False, index=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("customers.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("order_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("marketing_emails", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("restock_alerts", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("new_drops", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add abandoned_cart_email_sent flag to cart_items
    op.add_column("cart_items", sa.Column("abandoned_email_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("cart_items", "abandoned_email_sent")
    op.drop_table("notification_preferences")
    op.drop_table("email_logs")
