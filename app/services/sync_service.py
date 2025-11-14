"""Note synchronization service"""
from sqlalchemy.orm import Session
from app.models.note import EncryptedNote, SyncEvent
from app.models.user import User
from app.schemas.note import EncryptedNoteCreate
from app.services.usage_service import UsageService
from typing import List, Dict
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
            since_datetime = datetime.utcfromtimestamp(since)
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
        - Rate limiting for free tier users

        Args:
            user_id: User ID
            encrypted_notes: List of encrypted notes from client
            device_id: Device identifier

        Returns:
            Sync result with updated notes, conflicts, and usage stats
        """
        usage_service = UsageService(self.db)

        # Get user and check premium status
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "synced_count": 0,
                "updated_notes": [],
                "conflicts": [],
                "message": "User not found",
                "usage": None,
            }

        is_premium = user.is_premium

        # Count how many NEW notes we're trying to create (vs updates)
        new_notes_count = 0
        for note_data in encrypted_notes:
            existing_note = self.db.query(EncryptedNote).filter(
                EncryptedNote.user_id == user_id,
                EncryptedNote.client_note_uuid == note_data.client_note_uuid
            ).first()
            if not existing_note and not (note_data.metadata and note_data.metadata.is_deleted):
                new_notes_count += 1

        # For free users, check if they would exceed limit
        if not is_premium:
            current_usage = usage_service.get_or_create_usage_tracking(user_id)
            would_exceed_limit = (current_usage.synced_notes_count + new_notes_count) > 50

            if would_exceed_limit:
                # Calculate how many they can still sync
                remaining_slots = max(0, 50 - current_usage.synced_notes_count)

                return {
                    "synced_count": 0,
                    "updated_notes": [],
                    "conflicts": [],
                    "message": f"Sync limit exceeded. Free plan allows 50 notes. You have {current_usage.synced_notes_count} synced. Can sync {remaining_slots} more. Upgrade to Premium for unlimited sync.",
                    "limit_exceeded": True,
                    "usage": usage_service.get_user_usage(user_id),
                }

        synced_count = 0
        updated_notes = []
        conflicts = []
        new_notes_created = 0

        for note_data in encrypted_notes:
            # Check if note exists by UUID
            existing_note = self.db.query(EncryptedNote).filter(
                EncryptedNote.user_id == user_id,
                EncryptedNote.client_note_uuid == note_data.client_note_uuid
            ).first()

            # Decode base64 encrypted data
            try:
                encrypted_blob = base64.b64decode(note_data.encrypted_data)
            except Exception:
                conflicts.append({
                    "client_note_uuid": note_data.client_note_uuid,
                    "error": "Invalid base64 encoding"
                })
                continue

            if existing_note:
                # Update existing note
                # Simple conflict resolution: last write wins
                # TODO: Implement proper version-based conflict resolution

                existing_note.encrypted_data = encrypted_blob
                existing_note.note_metadata = note_data.metadata.dict() if note_data.metadata else None
                existing_note.version = note_data.version

                # IMPORTANT: Update is_deleted column from metadata
                # This ensures proper filtering and reconciliation
                if note_data.metadata and note_data.metadata.is_deleted is not None:
                    existing_note.is_deleted = note_data.metadata.is_deleted

                # IMPORTANT: Preserve client's timestamp from metadata
                # This ensures timestamps stay consistent across devices
                if note_data.metadata and note_data.metadata.updated_at:
                    try:
                        client_timestamp = datetime.fromisoformat(note_data.metadata.updated_at.replace('Z', '+00:00'))
                        existing_note.updated_at = client_timestamp
                    except Exception:
                        # Fallback to server time if client timestamp is invalid
                        existing_note.updated_at = datetime.utcnow()
                else:
                    existing_note.updated_at = datetime.utcnow()

                updated_notes.append(existing_note)
                synced_count += 1
            else:
                # Create new note (increment counter for free users)
                # Preserve client's timestamp if provided
                created_at = datetime.utcnow()
                updated_at = datetime.utcnow()

                if note_data.metadata and note_data.metadata.updated_at:
                    try:
                        client_timestamp = datetime.fromisoformat(note_data.metadata.updated_at.replace('Z', '+00:00'))
                        updated_at = client_timestamp
                        created_at = client_timestamp
                    except Exception:
                        pass  # Use server time

                # Set is_deleted from metadata
                is_deleted = note_data.metadata.is_deleted if note_data.metadata and note_data.metadata.is_deleted is not None else False

                new_note = EncryptedNote(
                    user_id=user_id,
                    client_note_id=note_data.client_note_id,  # Use client's DB ID for unique constraint
                    client_note_uuid=note_data.client_note_uuid,
                    encrypted_data=encrypted_blob,
                    note_metadata=note_data.metadata.dict() if note_data.metadata else None,
                    version=note_data.version,
                    is_deleted=is_deleted,
                    created_at=created_at,
                    updated_at=updated_at
                )

                self.db.add(new_note)
                updated_notes.append(new_note)
                synced_count += 1

                # Track new note creation
                if not (note_data.metadata and note_data.metadata.is_deleted):
                    new_notes_created += 1

        # Commit all changes
        try:
            self.db.commit()

            # Update usage counter for new notes (FREE USERS ONLY)
            # Premium users don't need tracking since they have unlimited
            if new_notes_created > 0 and not is_premium:
                usage_service.increment_synced_notes(user_id, new_notes_created)

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
                "message": f"Sync failed: {str(e)}",
                "usage": usage_service.get_user_usage(user_id),
            }

        # Convert encrypted_data back to base64 for response
        for note in updated_notes:
            note.encrypted_data = base64.b64encode(note.encrypted_data).decode('utf-8')

        # Get updated usage stats to send back to client
        usage_stats = usage_service.get_user_usage(user_id)

        return {
            "synced_count": synced_count,
            "updated_notes": updated_notes,
            "conflicts": conflicts,
            "message": f"Successfully synced {synced_count} notes",
            "usage": usage_stats,
        }

    def delete_notes(
        self,
        user_id: str,
        client_note_uuids: List[str],
        hard_delete: bool = False
    ) -> int:
        """
        Delete notes (soft delete by default)

        Args:
            user_id: User ID
            client_note_uuids: List of client note UUIDs to delete
            hard_delete: If True, permanently delete. If False, soft delete.

        Returns:
            Number of notes deleted
        """
        usage_service = UsageService(self.db)

        notes = self.db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.client_note_uuid.in_(client_note_uuids)
        )

        # Count notes before deletion for usage tracking
        count = notes.count()

        if hard_delete:
            notes.delete(synchronize_session=False)
        else:
            notes.update(
                {"is_deleted": True, "updated_at": datetime.utcnow()},
                synchronize_session=False
            )

        self.db.commit()

        # Decrement usage counter for deleted notes (FREE USERS ONLY)
        # Premium users don't track usage
        user = self.db.query(User).filter(User.id == user_id).first()
        if count > 0 and user and not user.is_premium:
            usage_service.decrement_synced_notes(user_id, count)

        return count
