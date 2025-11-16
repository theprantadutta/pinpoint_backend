"""add_reminders_table

Revision ID: 20251116_2100
Revises: f108e0b3764c
Create Date: 2025-11-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20251116_2100'
down_revision: Union[str, None] = 'f108e0b3764c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create reminders table for backend-controlled notification scheduling

    Stores reminder times unencrypted to enable Celery-based scheduling.
    Sends FCM push notifications to all user devices at scheduled time.
    """
    op.create_table(
        'reminders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_uuid', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reminder_time', sa.DateTime(), nullable=False),
        sa.Column('is_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # Indexes for efficient queries
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_reminder_time', 'reminders', ['reminder_time'])
    op.create_index('ix_reminders_is_triggered', 'reminders', ['is_triggered'])
    op.create_index('ix_reminders_note_uuid', 'reminders', ['note_uuid'])

    # Composite indexes for common query patterns
    op.create_index('ix_reminders_user_pending', 'reminders', ['user_id', 'is_triggered', 'reminder_time'])
    op.create_index('ix_reminders_due', 'reminders', ['is_triggered', 'reminder_time'])


def downgrade() -> None:
    """Drop reminders table and indexes"""
    op.drop_index('ix_reminders_due', table_name='reminders')
    op.drop_index('ix_reminders_user_pending', table_name='reminders')
    op.drop_index('ix_reminders_note_uuid', table_name='reminders')
    op.drop_index('ix_reminders_is_triggered', table_name='reminders')
    op.drop_index('ix_reminders_reminder_time', table_name='reminders')
    op.drop_index('ix_reminders_user_id', table_name='reminders')
    op.drop_table('reminders')
