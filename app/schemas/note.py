"""Note sync schemas"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional, Dict, Any


class NoteMetadata(BaseModel):
    """Non-sensitive metadata about a note"""
    type: str  # 'text', 'audio', 'todo', 'drawing'
    updated_at: str
    has_audio: bool = False
    has_attachments: bool = False
    is_archived: bool = False
    is_deleted: bool = False


class EncryptedNoteCreate(BaseModel):
    """Schema for uploading an encrypted note"""
    client_note_id: int  # Client's local database ID
    client_note_uuid: str  # Globally unique identifier from client
    encrypted_data: str  # Base64-encoded encrypted blob
    metadata: Optional[NoteMetadata] = None
    version: int = 1


class EncryptedNoteResponse(BaseModel):
    """Schema for encrypted note response"""
    id: UUID4
    client_note_uuid: str  # Globally unique identifier from client
    encrypted_data: str
    note_metadata: Optional[Dict[str, Any]] = None
    version: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class NoteSyncRequest(BaseModel):
    """Schema for batch note sync request"""
    notes: List[EncryptedNoteCreate]
    device_id: str


class NoteSyncResponse(BaseModel):
    """Schema for sync response"""
    synced_count: int
    updated_notes: List[EncryptedNoteResponse]
    conflicts: List[Dict[str, Any]] = []
    message: str


class NoteDeleteRequest(BaseModel):
    """Schema for deleting notes"""
    client_note_uuids: List[str]  # UUIDs of notes to delete
