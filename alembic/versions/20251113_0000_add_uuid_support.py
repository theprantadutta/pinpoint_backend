"""Add UUID support for notes, folders, and todos

Revision ID: 20251113_0000
Revises: 20251112_0200
Create Date: 2025-11-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251113_0000'
down_revision: Union[str, None] = '20251112_0200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================================
    # Step 1: Add UUID column for notes (nullable initially for migration)
    # ============================================================================
    op.add_column('encrypted_notes',
        sa.Column('client_note_uuid', sa.String(36), nullable=True))

    # ============================================================================
    # Step 2: Create migration mapping table for client UUID mapping
    # This allows clients to upload their old ID -> new UUID mapping
    # ============================================================================
    op.create_table('note_id_migration',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('old_client_note_id', sa.Integer(), nullable=False),
        sa.Column('new_client_note_uuid', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Add index for faster lookups during migration
    op.create_index('ix_note_id_migration_user_old_id',
                    'note_id_migration',
                    ['user_id', 'old_client_note_id'],
                    unique=True)

    # ============================================================================
    # Step 3: Backfill UUIDs for existing notes
    # Generate UUIDs for all existing encrypted notes
    # ============================================================================
    op.execute("""
        UPDATE encrypted_notes
        SET client_note_uuid = gen_random_uuid()::text
        WHERE client_note_uuid IS NULL
    """)

    # ============================================================================
    # Step 4: Make UUID column NOT NULL now that all rows have values
    # ============================================================================
    op.alter_column('encrypted_notes', 'client_note_uuid', nullable=False)

    # ============================================================================
    # Step 5: Add unique constraint on (user_id, client_note_uuid)
    # This ensures each user's note has a unique UUID
    # ============================================================================
    op.create_unique_constraint(
        'uq_user_client_note_uuid',
        'encrypted_notes',
        ['user_id', 'client_note_uuid']
    )

    # ============================================================================
    # Step 6: Keep old constraint temporarily for backwards compatibility
    # Will be removed in future migration after all clients are updated
    # ============================================================================
    # Note: The constraint 'uq_user_client_note' on (user_id, client_note_id)
    # already exists from migration 20251112_0000 and is kept intact

    # ============================================================================
    # Step 7: Add index on UUID for faster lookups
    # ============================================================================
    op.create_index('ix_encrypted_notes_client_uuid',
                    'encrypted_notes',
                    ['user_id', 'client_note_uuid'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_encrypted_notes_client_uuid', table_name='encrypted_notes')

    # Drop unique constraint
    op.drop_constraint('uq_user_client_note_uuid', 'encrypted_notes', type_='unique')

    # Drop UUID column
    op.drop_column('encrypted_notes', 'client_note_uuid')

    # Drop migration table
    op.drop_index('ix_note_id_migration_user_old_id', table_name='note_id_migration')
    op.drop_table('note_id_migration')
