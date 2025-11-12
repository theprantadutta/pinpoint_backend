"""Add unique constraint on (user_id, client_note_id)

Revision ID: 20251112_0000
Revises: 1cfc38a752d1
Create Date: 2025-11-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251112_0000'
down_revision: Union[str, None] = '1cfc38a752d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, we need to handle potential duplicate entries before adding the constraint
    # This SQL finds and deletes duplicate entries, keeping only the most recent one
    op.execute("""
        DELETE FROM encrypted_notes
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, client_note_id
                           ORDER BY updated_at DESC, created_at DESC
                       ) as rn
                FROM encrypted_notes
            ) t
            WHERE t.rn > 1
        )
    """)

    # Now add the unique constraint
    op.create_unique_constraint(
        'uq_user_client_note',
        'encrypted_notes',
        ['user_id', 'client_note_id']
    )


def downgrade() -> None:
    # Remove the unique constraint
    op.drop_constraint('uq_user_client_note', 'encrypted_notes', type_='unique')
