"""add grace period field to devices

Revision ID: 20251219_0000
Revises: 20251117_0100
Create Date: 2025-12-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251219_0000'
down_revision: Union[str, None] = '20251117_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add grace_period_ends_at column to devices table

    This enables grace period support for device-based subscriptions.
    When payment fails, users keep access for a few days (grace period)
    before losing premium features.
    """
    op.add_column('devices', sa.Column('grace_period_ends_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove grace_period_ends_at column from devices table"""
    op.drop_column('devices', 'grace_period_ends_at')
