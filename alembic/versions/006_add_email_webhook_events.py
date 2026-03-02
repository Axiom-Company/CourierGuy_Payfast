"""Add email_webhook_events table for ZeptoMail webhook tracking.

Revision ID: 006_email_webhooks
Revises: 005_seller_verifications
"""
from alembic import op
import sqlalchemy as sa

revision = "006_email_webhooks"
down_revision = "005_seller_verifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_webhook_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(30), nullable=False, index=True),
        sa.Column("recipient_email", sa.String(255), nullable=False, index=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("email_reference", sa.String(255), nullable=True, index=True),
        sa.Column("bounce_type", sa.String(30), nullable=True),
        sa.Column("bounce_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("email_webhook_events")
