"""Note synchronization service"""
from sqlalchemy.orm import Session
from app.models.note import EncryptedNote, SyncEvent
from app.schemas.note import EncryptedNoteCreate
from typing import List
import base64
from datetime import datetime


class SyncService:
    """Service for note synchronization"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_notes(
        self,
        user_id: str,
        since: int = 0,
        include_deleted: bool = False
    ) -> List[EncryptedNote]:
        """
        Get all notes for a user (for sync)

        Args:
            user_id: User ID
            since: Unix timestamp for incremental sync
            include_deleted: Whether to include soft-deleted notes

        Returns:
            List of encrypted notes
        """
        query = self.db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id
        )

        # Filter by timestamp for incremental sync
        if since > 0:
            since_datetime = datetime.fromtimestamp(since)
            query = query.filter(EncryptedNote.updated_at > since_datetime)

        # Optionally exclude deleted notes
        if not include_deleted:
            query = query.filter(EncryptedNote.is_deleted == False)

        return query.all()

    def sync_notes(
        self,
        user_id: str,
        encrypted_notes: List[EncryptedNoteCreate],
        device_id: str
    ) -> dict:
        """
        Sync notes from client to server

        This handles:
        - Creating new notes
        - Updating existing notes
        - Simple conflict resolution (last write wins for now)

        Args:
            user_id: User ID
            encrypted_notes: List of encrypted notes from client
            device_id: Device identifier

        Returns:
            Sync result with updated notes and conflicts
        """
        synced_count = 0
        updated_notes = []
        conflicts = []

        for note_data in encrypted_notes:
            # Check if note exists
            existing_note = self.db.query(EncryptedNote).filter(
                EncryptedNote.user_id == user_id,
                EncryptedNote.client_note_id == note_data.client_note_id
            ).first()

            # Decode base64 encrypted data
            try:
                encrypted_blob = base64.b64decode(note_data.encrypted_data)
            except Exception:
                conflicts.append({
                    "client_note_id": note_data.client_note_id,
                    "error": "Invalid base64 encoding"
                })
                continue

            if existing_note:
                # Update existing note
                # Simple conflict resolution: last write wins
                # TODO: Implement proper version-based conflict resolution

                existing_note.encrypted_data = encrypted_blob
                existing_note.metadata = note_data.metadata.dict() if note_data.metadata else None
                existing_note.version = note_data.version
                existing_note.updated_at = datetime.utcnow()

                updated_notes.append(existing_note)
                synced_count += 1
            else:
                # Create new note
                new_note = EncryptedNote(
                    user_id=user_id,
                    client_note_id=note_data.client_note_id,
                    encrypted_data=encrypted_blob,
                    metadata=note_data.metadata.dict() if note_data.metadata else None,
                    version=note_data.version
                )

                self.db.add(new_note)
                updated_notes.append(new_note)
                synced_count += 1

        # Commit all changes
        try:
            self.db.commit()

            # Refresh all notes to get updated timestamps
            for note in updated_notes:
                self.db.refresh(note)

            # Log sync event
            sync_event = SyncEvent(
                user_id=user_id,
                device_id=device_id,
                notes_synced=synced_count,
                status="success"
            )
            self.db.add(sync_event)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            return {
                "synced_count": 0,
                "updated_notes": [],
                "conflicts": conflicts,
                "message": f"Sync failed: {str(e)}"
            }

        # Convert encrypted_data back to base64 for response
        for note in updated_notes:
            note.encrypted_data = base64.b64encode(note.encrypted_data).decode('utf-8')

        return {
            "synced_count": synced_count,
            "updated_notes": updated_notes,
            "conflicts": conflicts,
            "message": f"Successfully synced {synced_count} notes"
        }

    def delete_notes(
        self,
        user_id: str,
        client_note_ids: List[int],
        hard_delete: bool = False
    ) -> int:
        """
        Delete notes (soft delete by default)

        Args:
            user_id: User ID
            client_note_ids: List of client note IDs to delete
            hard_delete: If True, permanently delete. If False, soft delete.

        Returns:
            Number of notes deleted
        """
        notes = self.db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.client_note_id.in_(client_note_ids)
        )

        if hard_delete:
            count = notes.delete(synchronize_session=False)
        else:
            count = notes.update(
                {"is_deleted": True, "updated_at": datetime.utcnow()},
                synchronize_session=False
            )

        self.db.commit()
        return count
