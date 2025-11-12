"""add admin audit logs table

Revision ID: 20251112_0100
Revises: 20251112_0000
Create Date: 2025-11-12 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '20251112_0100'
down_revision: Union[str, None] = '20251112_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_email', sa.String(255), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('request_data', JSONB, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
    )


def downgrade() -> None:
    # Drop admin_audit_logs table
    op.drop_table('admin_audit_logs')
