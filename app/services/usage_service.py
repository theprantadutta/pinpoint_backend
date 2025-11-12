"""
Usage tracking and rate limiting service

Handles all usage tracking, limit enforcement, and monthly resets
for free tier users.
"""
from sqlalchemy.orm import Session
from app.models.user import User, UsageTracking
from app.models.note import EncryptedNote
from typing import Dict, Optional
from datetime import datetime


# Free tier limits (premium users have unlimited)
FREE_TIER_LIMITS = {
    "synced_notes": 50,
    "ocr_scans_month": 20,
    "exports_month": 10,
}


class UsageService:
    """Service for tracking user usage and enforcing rate limits"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_usage_tracking(self, user_id: str) -> UsageTracking:
        """
        Get existing usage tracking record or create a new one.

        Args:
            user_id: User's UUID

        Returns:
            UsageTracking record
        """
        tracking = self.db.query(UsageTracking).filter(
            UsageTracking.user_id == user_id
        ).first()

        if not tracking:
            # Create new tracking record with defaults
            tracking = UsageTracking(user_id=user_id)
            self.db.add(tracking)
            self.db.commit()
            self.db.refresh(tracking)

        # Check and reset monthly counters if needed
        if tracking.check_and_reset_monthly():
            self.db.commit()
            self.db.refresh(tracking)

        return tracking

    def get_user_usage(self, user_id: str) -> Dict:
        """
        Get comprehensive usage statistics for a user.

        Args:
            user_id: User's UUID

        Returns:
            Dict with usage stats for all tracked features
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        tracking = self.get_or_create_usage_tracking(user_id)
        is_premium = user.is_premium

        return {
            "is_premium": is_premium,
            "subscription_tier": user.subscription_tier,
            "synced_notes": {
                "current": tracking.synced_notes_count,
                "limit": -1 if is_premium else FREE_TIER_LIMITS["synced_notes"],
                "unlimited": is_premium,
                "remaining": -1 if is_premium else max(0, FREE_TIER_LIMITS["synced_notes"] - tracking.synced_notes_count),
            },
            "ocr_scans": {
                "current": tracking.ocr_scans_month,
                "limit": -1 if is_premium else FREE_TIER_LIMITS["ocr_scans_month"],
                "unlimited": is_premium,
                "remaining": -1 if is_premium else max(0, FREE_TIER_LIMITS["ocr_scans_month"] - tracking.ocr_scans_month),
                "resets_at": self._get_next_month_start().isoformat(),
            },
            "exports": {
                "current": tracking.exports_month,
                "limit": -1 if is_premium else FREE_TIER_LIMITS["exports_month"],
                "unlimited": is_premium,
                "remaining": -1 if is_premium else max(0, FREE_TIER_LIMITS["exports_month"] - tracking.exports_month),
                "resets_at": self._get_next_month_start().isoformat(),
            },
            "last_updated": tracking.updated_at.isoformat(),
        }

    def can_sync_note(self, user_id: str) -> bool:
        """
        Check if user can sync a new note.

        Premium users always return True.
        Free users are limited to 50 synced notes.

        Args:
            user_id: User's UUID

        Returns:
            True if user can sync, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Premium users have unlimited sync
        if user.is_premium:
            return True

        # Check free tier limit
        tracking = self.get_or_create_usage_tracking(user_id)
        return tracking.synced_notes_count < FREE_TIER_LIMITS["synced_notes"]

    def can_perform_ocr(self, user_id: str) -> bool:
        """
        Check if user can perform OCR scan.

        Premium users always return True.
        Free users are limited to 20 OCR scans per month.

        Args:
            user_id: User's UUID

        Returns:
            True if user can perform OCR, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Premium users have unlimited OCR
        if user.is_premium:
            return True

        # Check free tier limit
        tracking = self.get_or_create_usage_tracking(user_id)
        return tracking.ocr_scans_month < FREE_TIER_LIMITS["ocr_scans_month"]

    def can_export(self, user_id: str) -> bool:
        """
        Check if user can export notes.

        Premium users always return True.
        Free users are limited to 10 exports per month.

        Args:
            user_id: User's UUID

        Returns:
            True if user can export, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Premium users have unlimited exports
        if user.is_premium:
            return True

        # Check free tier limit
        tracking = self.get_or_create_usage_tracking(user_id)
        return tracking.exports_month < FREE_TIER_LIMITS["exports_month"]

    def increment_synced_notes(self, user_id: str, count: int = 1) -> None:
        """
        Increment the synced notes counter.

        Args:
            user_id: User's UUID
            count: Number to increment (default: 1)
        """
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.synced_notes_count += count
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

    def decrement_synced_notes(self, user_id: str, count: int = 1) -> None:
        """
        Decrement the synced notes counter (when notes are deleted).

        Args:
            user_id: User's UUID
            count: Number to decrement (default: 1)
        """
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.synced_notes_count = max(0, tracking.synced_notes_count - count)
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

    def increment_ocr_scans(self, user_id: str, count: int = 1) -> None:
        """
        Increment the monthly OCR scans counter.

        Args:
            user_id: User's UUID
            count: Number to increment (default: 1)
        """
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.ocr_scans_month += count
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

    def increment_exports(self, user_id: str, count: int = 1) -> None:
        """
        Increment the monthly exports counter.

        Args:
            user_id: User's UUID
            count: Number to increment (default: 1)
        """
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.exports_month += count
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

    def reconcile_synced_notes_count(self, user_id: str) -> int:
        """
        Reconcile synced notes count with actual database count.

        Counts non-deleted notes in the database and updates the tracking record.

        Args:
            user_id: User's UUID

        Returns:
            The reconciled count
        """
        # Count actual non-deleted notes in database
        actual_count = self.db.query(EncryptedNote).filter(
            EncryptedNote.user_id == user_id,
            EncryptedNote.is_deleted == False
        ).count()

        # Update tracking record
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.synced_notes_count = actual_count
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

        return actual_count

    def set_synced_notes_count(self, user_id: str, count: int) -> None:
        """
        Directly set the synced notes counter (for migrations/reconciliation).

        Args:
            user_id: User's UUID
            count: New count value
        """
        tracking = self.get_or_create_usage_tracking(user_id)
        tracking.synced_notes_count = max(0, count)
        tracking.updated_at = datetime.utcnow()
        self.db.commit()

    def _get_next_month_start(self) -> datetime:
        """Get the start of next month (for reset countdown)."""
        from calendar import monthrange

        now = datetime.utcnow()
        # Get the last day of current month
        last_day = monthrange(now.year, now.month)[1]

        # If today is the last day, next month starts tomorrow
        if now.day == last_day:
            return datetime(now.year, now.month, last_day, 23, 59, 59)

        # Otherwise, calculate next month's start
        next_month = now.month + 1
        next_year = now.year

        if next_month > 12:
            next_month = 1
            next_year += 1

        return datetime(next_year, next_month, 1, 0, 0, 0)
