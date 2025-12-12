"""add firebase authentication fields

Revision ID: 20251108_2345
Revises:
Create Date: 2025-11-08 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251108_2345'
down_revision: Union[str, None] = '20251108_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make password_hash nullable for Google-only users
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=True)

    # Add Firebase/Google authentication columns
    op.add_column('users', sa.Column('firebase_uid', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(50), nullable=False, server_default='email'))
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('photo_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))

    # Create indexes for performance
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_index('ix_users_firebase_uid', table_name='users')

    # Drop columns
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'photo_url')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'firebase_uid')

    # Make password_hash not nullable again
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=False)
