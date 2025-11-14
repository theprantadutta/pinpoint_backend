"""Folder model for organizing notes"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.base_class import Base


class Folder(Base):
    """
    Folder model for organizing notes

    Folders are NOT encrypted (non-sensitive data - just organizational)
    Uses deterministic UUIDs from client for cross-device consistency
    """
    __tablename__ = "folders"

    # Server-side unique ID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User who owns this folder
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Client-generated deterministic UUID (UUID v5 based on folder name)
    # This ensures the same folder name always gets the same UUID across devices
    uuid = Column(String, nullable=False)

    # Folder title (e.g., "Random", "HomeWork", "Workout")
    title = Column(String, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: Each user can have a folder with a specific UUID only once
    __table_args__ = (
        UniqueConstraint('user_id', 'uuid', name='uq_user_folder_uuid'),
    )

    # Relationships (optional - folders don't track which notes they contain server-side)
    user = relationship("User", back_populates="folders")

    def __repr__(self):
        return f"<Folder(uuid='{self.uuid}', title='{self.title}', user_id='{self.user_id}')>"
