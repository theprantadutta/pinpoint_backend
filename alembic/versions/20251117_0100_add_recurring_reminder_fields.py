"""add_recurring_reminder_fields

Revision ID: 20251117_0100
Revises: 20251116_2100
Create Date: 2025-11-17 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20251117_0100'
down_revision: Union[str, None] = '20251116_2100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add recurring reminder fields to reminders table

    New fields:
    - notification_title: Separate title for push notification (different from note title)
    - notification_content: Content for notification body (replaces description)
    - recurrence_type: Type of recurrence (once, hourly, daily, weekly, monthly, yearly)
    - recurrence_interval: Interval for recurrence (e.g., every 2 days)
    - recurrence_end_type: How the recurrence ends (never, after_occurrences, on_date)
    - recurrence_end_value: Value for end condition (number or ISO date string)
    - parent_reminder_id: Link to parent reminder for series tracking
    - occurrence_number: Which occurrence in the series (1, 2, 3...)
    - series_id: UUID to group all occurrences of same recurring reminder
    """

    # Add new columns
    op.add_column('reminders', sa.Column('notification_title', sa.String(500), nullable=True))
    op.add_column('reminders', sa.Column('notification_content', sa.Text(), nullable=True))
    op.add_column('reminders', sa.Column('recurrence_type', sa.String(20), nullable=False, server_default='once'))
    op.add_column('reminders', sa.Column('recurrence_interval', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('reminders', sa.Column('recurrence_end_type', sa.String(20), nullable=False, server_default='never'))
    op.add_column('reminders', sa.Column('recurrence_end_value', sa.String(100), nullable=True))
    op.add_column('reminders', sa.Column('parent_reminder_id', UUID(as_uuid=True), nullable=True))
    op.add_column('reminders', sa.Column('occurrence_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('reminders', sa.Column('series_id', UUID(as_uuid=True), nullable=True))

    # Migrate existing data
    # Copy title to notification_title, description to notification_content
    op.execute("""
        UPDATE reminders
        SET notification_title = title,
            notification_content = description
        WHERE notification_title IS NULL
    """)

    # Make notification_title NOT NULL after migration
    op.alter_column('reminders', 'notification_title', nullable=False)

    # Add foreign key for parent_reminder_id (self-referencing)
    op.create_foreign_key(
        'fk_reminders_parent_reminder_id',
        'reminders',
        'reminders',
        ['parent_reminder_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add indexes for efficient queries
    op.create_index('ix_reminders_series_id', 'reminders', ['series_id'])
    op.create_index('ix_reminders_parent_reminder_id', 'reminders', ['parent_reminder_id'])
    op.create_index('ix_reminders_recurrence_type', 'reminders', ['recurrence_type'])


def downgrade() -> None:
    """Drop recurring reminder fields"""

    # Drop indexes
    op.drop_index('ix_reminders_recurrence_type', table_name='reminders')
    op.drop_index('ix_reminders_parent_reminder_id', table_name='reminders')
    op.drop_index('ix_reminders_series_id', table_name='reminders')

    # Drop foreign key
    op.drop_constraint('fk_reminders_parent_reminder_id', 'reminders', type_='foreignkey')

    # Drop columns
    op.drop_column('reminders', 'series_id')
    op.drop_column('reminders', 'occurrence_number')
    op.drop_column('reminders', 'parent_reminder_id')
    op.drop_column('reminders', 'recurrence_end_value')
    op.drop_column('reminders', 'recurrence_end_type')
    op.drop_column('reminders', 'recurrence_interval')
    op.drop_column('reminders', 'recurrence_type')
    op.drop_column('reminders', 'notification_content')
    op.drop_column('reminders', 'notification_title')
