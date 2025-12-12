"""initial schema - create base tables

Revision ID: 20251108_0000
Revises:
Create Date: 2025-11-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20251108_0000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table (base columns before firebase auth)
    # Note: unique=True on column already creates an index, so we don't need explicit create_index
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('subscription_tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('google_play_purchase_token', sa.String(500), nullable=True),
        sa.Column('device_id', sa.String(255), nullable=True),
        sa.Column('public_key', sa.Text(), nullable=True),
    )

    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(255), unique=True, nullable=False),
        sa.Column('subscription_tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('subscription_product_id', sa.String(100), nullable=True),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_purchase_token', sa.String(500), nullable=True),
        sa.Column('purchase_verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create encrypted_notes table (without client_note_uuid - added in later migration)
    op.create_table(
        'encrypted_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_note_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_data', sa.LargeBinary(), nullable=False),
        sa.Column('note_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_encrypted_notes_user_id', 'encrypted_notes', ['user_id'])

    # Create sync_events table
    op.create_table(
        'sync_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('sync_timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes_synced', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(50), nullable=False),
    )
    op.create_index('ix_sync_events_user_id', 'sync_events', ['user_id'])

    # Create subscription_events table
    op.create_table(
        'subscription_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('purchase_token', sa.String(500), nullable=True),
        sa.Column('product_id', sa.String(100), nullable=True),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('raw_receipt', sa.Text(), nullable=True),
    )
    op.create_index('ix_subscription_events_user_id', 'subscription_events', ['user_id'])

    # Create fcm_tokens table
    op.create_table(
        'fcm_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('fcm_token', sa.String(500), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_fcm_tokens_user_id', 'fcm_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_table('fcm_tokens')
    op.drop_table('subscription_events')
    op.drop_table('sync_events')
    op.drop_table('encrypted_notes')
    op.drop_table('devices')
    op.drop_table('users')
