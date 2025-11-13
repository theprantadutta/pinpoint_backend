"""User model"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class User(Base):
    """User account model"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for Google-only users

    # Firebase/Google Authentication
    firebase_uid = Column(String(255), unique=True, nullable=True, index=True)
    auth_provider = Column(String(50), default="email", nullable=False)  # 'email', 'google', 'firebase'
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    photo_url = Column(Text, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Profile
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Subscription
    subscription_tier = Column(String(50), default="free", nullable=False)
    subscription_expires_at = Column(DateTime, nullable=True)
    grace_period_ends_at = Column(DateTime, nullable=True)
    google_play_purchase_token = Column(String(500), nullable=True)

    # Device info
    device_id = Column(String(255), nullable=True)

    # End-to-end encryption
    public_key = Column(Text, nullable=True)  # For future E2E encryption features

    # Relationships
    notes = relationship("EncryptedNote", back_populates="user", cascade="all, delete-orphan")
    note_id_migrations = relationship("NoteIdMigration", back_populates="user", cascade="all, delete-orphan")
    sync_events = relationship("SyncEvent", back_populates="user", cascade="all, delete-orphan")
    subscription_events = relationship("SubscriptionEvent", back_populates="user", cascade="all, delete-orphan")
    fcm_tokens = relationship("FCMToken", back_populates="user", cascade="all, delete-orphan")
    encryption_key = relationship("EncryptionKey", back_populates="user", cascade="all, delete-orphan", uselist=False)
    usage_tracking = relationship("UsageTracking", back_populates="user", cascade="all, delete-orphan", uselist=False)

    @property
    def is_premium(self) -> bool:
        """Check if user has active premium subscription or in grace period"""
        # Check if in grace period first
        if self.is_in_grace_period():
            return True

        if self.subscription_tier == "free":
            return False

        # Lifetime subscriptions never expire
        if self.subscription_tier == "lifetime":
            return True

        # For premium/premium_yearly, check expiration
        if self.subscription_tier in ["premium", "premium_yearly"]:
            # If no expiration date set, treat as lifetime (shouldn't happen, but handle gracefully)
            if self.subscription_expires_at is None:
                return True
            # Check if subscription hasn't expired
            return datetime.utcnow() < self.subscription_expires_at

        # Unknown tier, treat as not premium
        return False

    def is_in_grace_period(self) -> bool:
        """Check if user is currently in grace period"""
        if self.grace_period_ends_at is None:
            return False
        return datetime.utcnow() < self.grace_period_ends_at

    def start_grace_period(self, days: int = 3):
        """Start grace period for user"""
        from datetime import timedelta
        self.grace_period_ends_at = datetime.utcnow() + timedelta(days=days)

    def clear_grace_period(self):
        """Clear grace period (e.g., when payment succeeds)"""
        self.grace_period_ends_at = None

    def get_subscription_status(self) -> str:
        """Get detailed subscription status"""
        if self.is_in_grace_period():
            return "grace_period"
        elif self.is_premium:
            if self.subscription_tier == "lifetime":
                return "active_lifetime"
            return "active"
        elif self.subscription_expires_at and datetime.utcnow() < self.subscription_expires_at:
            # Within free trial period
            return "trial"
        else:
            return "expired"

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, tier={self.subscription_tier})>"


class UsageTracking(Base):
    """
    Track user usage for rate limiting and premium features

    This model stores counters for various usage metrics to enforce
    free tier limits and track premium feature usage.
    """

    __tablename__ = "usage_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Permanent counters (never reset)
    synced_notes_count = Column(Integer, default=0, nullable=False)  # Total notes synced to cloud

    # Monthly counters (reset on 1st of each month)
    ocr_scans_month = Column(Integer, default=0, nullable=False)  # OCR scans this month
    exports_month = Column(Integer, default=0, nullable=False)  # Exports (PDF/markdown) this month

    # Monthly reset tracking
    last_monthly_reset = Column(DateTime, default=datetime.utcnow, nullable=False)  # When monthly counters were last reset

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="usage_tracking")

    def check_and_reset_monthly(self) -> bool:
        """
        Check if monthly counters should be reset and reset them if needed.
        Returns True if reset was performed.
        """
        now = datetime.utcnow()
        last_reset = self.last_monthly_reset

        # Check if we're in a new month
        if now.year > last_reset.year or now.month > last_reset.month:
            self.ocr_scans_month = 0
            self.exports_month = 0
            self.last_monthly_reset = now
            self.updated_at = now
            return True

        return False

    def __repr__(self):
        return f"<UsageTracking(user_id={self.user_id}, synced_notes={self.synced_notes_count}, ocr={self.ocr_scans_month}, exports={self.exports_month})>"
