"""add usage tracking table

Revision ID: 20251112_0200
Revises: 20251112_0100
Create Date: 2025-11-12 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision: str = '20251112_0200'
down_revision: Union[str, None] = '20251112_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create usage_tracking table
    op.create_table(
        'usage_tracking',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('synced_notes_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('ocr_scans_month', sa.Integer, nullable=False, server_default='0'),
        sa.Column('exports_month', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_monthly_reset', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create index on user_id for faster lookups
    op.create_index('idx_usage_tracking_user_id', 'usage_tracking', ['user_id'], unique=True)


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_usage_tracking_user_id', table_name='usage_tracking')

    # Drop usage_tracking table
    op.drop_table('usage_tracking')
