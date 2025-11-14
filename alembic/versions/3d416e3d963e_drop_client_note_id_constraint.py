"""drop_client_note_id_constraint

Revision ID: 3d416e3d963e
Revises: 20251113_0000
Create Date: 2025-11-14 13:16:21.411215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d416e3d963e'
down_revision: Union[str, None] = '20251113_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique constraint on (user_id, client_note_id)
    # This constraint causes issues because client_note_id resets on app reinstall
    # We keep the uq_user_client_note_uuid constraint which uses UUIDs
    op.drop_constraint('uq_user_client_note', 'encrypted_notes', type_='unique')


def downgrade() -> None:
    # Recreate the constraint if rolling back
    op.create_unique_constraint('uq_user_client_note', 'encrypted_notes', ['user_id', 'client_note_id'])
