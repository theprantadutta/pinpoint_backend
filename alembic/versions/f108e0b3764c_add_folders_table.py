"""add_folders_table

Revision ID: f108e0b3764c
Revises: 3d416e3d963e
Create Date: 2025-11-14 15:58:42.713359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f108e0b3764c'
down_revision: Union[str, None] = '3d416e3d963e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create folders table for organizing notes

    Folders are NOT encrypted (non-sensitive organizational data).
    Uses deterministic UUIDs (v5) from client for cross-device consistency.
    """
    op.create_table(
        'folders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uuid', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'uuid', name='uq_user_folder_uuid'),
    )

    # Add index on user_id for faster queries
    op.create_index('idx_folders_user_id', 'folders', ['user_id'])


def downgrade() -> None:
    """Drop folders table"""
    op.drop_index('idx_folders_user_id', table_name='folders')
    op.drop_table('folders')
