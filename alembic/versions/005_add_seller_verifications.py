"""Add seller_verifications table for ID + face verification.

Revision ID: 005_seller_verifications
Revises: 004_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = '005_seller_verifications'
down_revision = '004_profiles'
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


def upgrade() -> None:
    if not _table_exists('seller_verifications'):
        op.create_table(
            'seller_verifications',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('customer_id', sa.String(255), nullable=False, index=True),
            sa.Column('status', sa.String(30), nullable=False, server_default='pending', index=True),

            # ID document info
            sa.Column('id_type', sa.String(30), nullable=False),
            sa.Column('id_front_image', sa.Text(), nullable=True),
            sa.Column('id_back_image', sa.Text(), nullable=True),
            sa.Column('selfie_image', sa.Text(), nullable=True),

            # Extracted / verified data
            sa.Column('id_number_hash', sa.String(255), nullable=True),
            sa.Column('full_name_on_id', sa.String(255), nullable=True),
            sa.Column('ocr_text_front', sa.Text(), nullable=True),
            sa.Column('ocr_text_back', sa.Text(), nullable=True),

            # Face verification results
            sa.Column('face_match_confidence', sa.Float(), nullable=True),
            sa.Column('face_match_passed', sa.Boolean(), nullable=True),
            sa.Column('faces_detected_id', sa.Integer(), nullable=True),
            sa.Column('faces_detected_selfie', sa.Integer(), nullable=True),

            # Admin review
            sa.Column('reviewed_by', sa.String(255), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('admin_notes', sa.Text(), nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )


def downgrade() -> None:
    if _table_exists('seller_verifications'):
        op.drop_table('seller_verifications')
