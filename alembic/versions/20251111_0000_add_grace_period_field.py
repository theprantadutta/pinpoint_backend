"""add grace period field to users

Revision ID: 20251111_0000
Revises: 20251108_2345
Create Date: 2025-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251111_0000'
down_revision: Union[str, None] = '20251108_2345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add grace_period_ends_at column to users table
    op.add_column('users', sa.Column('grace_period_ends_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove grace_period_ends_at column
    op.drop_column('users', 'grace_period_ends_at')
