"""Admin service for user and data management"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.user import User
from app.models.note import EncryptedNote, EncryptionKey, SyncEvent
from app.models.subscription import SubscriptionEvent
from typing import List, Dict, Any, Tuple, Optional
import base64


class AdminService:
    """Service layer for admin panel operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_users_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of users with optional search

        Args:
            page: Page number (1-indexed)
            page_size: Number of users per page
            search: Optional search query for email or display name

        Returns:
            Tuple of (users list, total count)
        """
        query = self.db.query(User)

        # Apply search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_pattern)) |
                (User.display_name.ilike(search_pattern))
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        users = query.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()

        # Format response
        users_data = []
        for user in users:
            users_data.append({
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "subscription_tier": user.subscription_tier,
                "is_premium": user.is_premium,
                "is_active": user.is_active,
                "auth_provider": user.auth_provider,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            })

        return users_data, total

    def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific user

        Args:
            user_id: UUID of the user

        Returns:
            Dict with comprehensive user information or None if not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Calculate statistics
        total_notes = self.db.query(func.count(EncryptedNote.id)).filter(
            EncryptedNote.user_id == user_id
        ).scalar()

        synced_notes = self.db.query(func.count(EncryptedNote.id)).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.is_deleted == False
        ).scalar()

        deleted_notes = self.db.query(func.count(EncryptedNote.id)).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.is_deleted == True
        ).scalar()

        # Get last sync event
        last_sync_event = self.db.query(SyncEvent).filter(
            SyncEvent.user_id == user_id
        ).order_by(desc(SyncEvent.sync_timestamp)).first()

        return {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "is_active": user.is_active,
            "auth_provider": user.auth_provider,
            "firebase_uid": user.firebase_uid,
            "google_id": user.google_id,
            "email_verified": user.email_verified,
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at,
            "grace_period_ends_at": user.grace_period_ends_at,
            "is_premium": user.is_premium,
            "subscription_status": user.get_subscription_status(),
            "device_id": user.device_id,
            "total_notes": total_notes,
            "synced_notes": synced_notes,
            "deleted_notes": deleted_notes,
            "last_sync": last_sync_event.sync_timestamp if last_sync_event else None,
        }

    def get_user_notes_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of user's notes

        WARNING: This returns encrypted note data. Handle with care.

        Args:
            user_id: UUID of the user
            page: Page number (1-indexed)
            page_size: Number of notes per page
            include_deleted: Whether to include soft-deleted notes

        Returns:
            Tuple of (notes list, total count)
        """
        query = self.db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(EncryptedNote.is_deleted == False)

        total = query.count()

        offset = (page - 1) * page_size
        notes = query.order_by(desc(EncryptedNote.updated_at)).offset(offset).limit(page_size).all()

        notes_data = []
        for note in notes:
            notes_data.append({
                "id": str(note.id),
                "client_note_id": note.client_note_id,
                "encrypted_data": base64.b64encode(note.encrypted_data).decode('utf-8'),
                "metadata": note.note_metadata,
                "version": note.version,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
                "is_deleted": note.is_deleted,
            })

        return notes_data, total

    def get_user_encryption_key(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's encryption key

        CRITICAL: This is EXTREMELY SENSITIVE data.
        With this key, ALL user notes can be decrypted.
        Access should be logged and monitored.

        Args:
            user_id: UUID of the user

        Returns:
            Dict with encryption key details or None if not found
        """
        encryption_key = self.db.query(EncryptionKey).filter(
            EncryptionKey.user_id == user_id
        ).first()

        if not encryption_key:
            return None

        return {
            "user_id": str(encryption_key.user_id),
            "encryption_key": encryption_key.encryption_key,  # Base64 encoded key
            "created_at": encryption_key.created_at,
            "updated_at": encryption_key.updated_at,
        }

    def get_user_sync_events(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's sync event history

        Args:
            user_id: UUID of the user
            limit: Maximum number of events to return

        Returns:
            List of sync events, newest first
        """
        events = self.db.query(SyncEvent).filter(
            SyncEvent.user_id == user_id
        ).order_by(desc(SyncEvent.sync_timestamp)).limit(limit).all()

        return [{
            "id": str(event.id),
            "device_id": event.device_id,
            "sync_timestamp": event.sync_timestamp.isoformat(),
            "notes_synced": event.notes_synced,
            "status": event.status,
        } for event in events]

    def get_user_subscription_events(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's subscription event history

        Args:
            user_id: UUID of the user
            limit: Maximum number of events to return

        Returns:
            List of subscription events, newest first
        """
        events = self.db.query(SubscriptionEvent).filter(
            SubscriptionEvent.user_id == user_id
        ).order_by(desc(SubscriptionEvent.verified_at)).limit(limit).all()

        return [{
            "id": str(event.id),
            "event_type": event.event_type,
            "product_id": event.product_id,
            "platform": event.platform,
            "verified_at": event.verified_at.isoformat(),
            "expires_at": event.expires_at.isoformat() if event.expires_at else None,
        } for event in events]
