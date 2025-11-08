"""Note synchronization endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.note import (
    EncryptedNoteResponse,
    NoteSyncRequest,
    NoteSyncResponse,
    NoteDeleteRequest
)
from app.services.sync_service import SyncService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/sync", response_model=List[EncryptedNoteResponse])
async def get_notes_for_sync(
    since: int = Query(0, description="Unix timestamp for incremental sync"),
    include_deleted: bool = Query(False, description="Include soft-deleted notes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all encrypted notes for sync

    Notes are encrypted client-side. Server cannot read content.

    - **since**: Unix timestamp (0 for full sync, timestamp for incremental)
    - **include_deleted**: Include soft-deleted notes
    """
    sync_service = SyncService(db)

    notes = sync_service.get_user_notes(
        user_id=str(current_user.id),
        since=since,
        include_deleted=include_deleted
    )

    # Convert encrypted_data to base64
    import base64
    for note in notes:
        note.encrypted_data = base64.b64encode(note.encrypted_data).decode('utf-8')

    return notes


@router.post("/sync", response_model=NoteSyncResponse)
async def sync_notes(
    sync_request: NoteSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload encrypted notes for synchronization

    Client encrypts notes before sending. Server stores encrypted blobs.

    - **notes**: List of encrypted notes
    - **device_id**: Unique device identifier
    """
    sync_service = SyncService(db)

    result = sync_service.sync_notes(
        user_id=str(current_user.id),
        encrypted_notes=sync_request.notes,
        device_id=sync_request.device_id
    )

    return result


@router.delete("/notes")
async def delete_notes(
    delete_request: NoteDeleteRequest,
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete notes (soft delete by default)

    - **client_note_ids**: List of note IDs to delete
    - **hard_delete**: If true, permanently delete. Otherwise soft delete.
    """
    sync_service = SyncService(db)

    deleted_count = sync_service.delete_notes(
        user_id=str(current_user.id),
        client_note_ids=delete_request.client_note_ids,
        hard_delete=hard_delete
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} note(s)"
    }
