"""Note and sync models"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class EncryptedNote(Base):
    """
    Encrypted note storage

    Notes are encrypted client-side before being sent to the server.
    The server stores encrypted blobs and cannot read the content.
    """

    __tablename__ = "encrypted_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_note_id = Column(Integer, nullable=False)  # Local ID from Flutter app

    # Encrypted data (server cannot read this)
    encrypted_data = Column(LargeBinary, nullable=False)

    # Non-sensitive metadata (not encrypted)
    note_metadata = Column(JSONB, nullable=True)  # {"type": "text", "has_audio": false, etc}

    # Versioning for conflict resolution
    version = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<EncryptedNote(id={self.id}, user_id={self.user_id}, client_id={self.client_note_id})>"


class SyncEvent(Base):
    """Track sync operations for debugging and analytics"""

    __tablename__ = "sync_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)

    sync_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes_synced = Column(Integer, default=0)
    status = Column(String(50), nullable=False)  # 'success', 'partial', 'failed'

    # Relationships
    user = relationship("User", back_populates="sync_events")

    def __repr__(self):
        return f"<SyncEvent(id={self.id}, user_id={self.user_id}, status={self.status})>"
