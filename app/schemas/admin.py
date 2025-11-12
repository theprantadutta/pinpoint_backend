"""Admin panel schemas"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


class AdminLoginRequest(BaseModel):
    """Admin password verification request"""
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    """Admin login response with special JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserListItem(BaseModel):
    """User item in list view"""
    id: str
    email: str
    display_name: Optional[str]
    subscription_tier: str
    is_premium: bool
    is_active: bool
    auth_provider: str
    created_at: str
    last_login: Optional[str]


class UserListResponse(BaseModel):
    """Response for paginated user list"""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserDetailResponse(BaseModel):
    """Detailed user information for admin"""
    id: str
    email: str
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

    # Auth
    auth_provider: str
    firebase_uid: Optional[str]
    google_id: Optional[str]
    email_verified: bool

    # Subscription
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    grace_period_ends_at: Optional[datetime]
    is_premium: bool
    subscription_status: str

    # Device
    device_id: Optional[str]

    # Stats
    total_notes: int
    synced_notes: int
    deleted_notes: int
    last_sync: Optional[datetime]


class NoteItem(BaseModel):
    """Note item in list view"""
    id: str
    client_note_id: int
    encrypted_data: str  # Base64
    metadata: Optional[Dict[str, Any]]
    version: int
    created_at: str
    updated_at: str
    is_deleted: bool


class NoteListResponse(BaseModel):
    """Response for paginated note list"""
    notes: List[NoteItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EncryptionKeyResponse(BaseModel):
    """Encryption key for admin view - EXTREMELY SENSITIVE"""
    user_id: str
    encryption_key: str  # Base64 encryption key
    created_at: datetime
    updated_at: datetime


class SyncEventItem(BaseModel):
    """Sync event item"""
    id: str
    device_id: str
    sync_timestamp: str
    notes_synced: int
    status: str


class SyncEventsResponse(BaseModel):
    """Response for sync events"""
    sync_events: List[SyncEventItem]
    count: int


class SubscriptionEventItem(BaseModel):
    """Subscription event item"""
    id: str
    event_type: str
    product_id: str
    platform: str
    verified_at: str
    expires_at: Optional[str]


class SubscriptionEventsResponse(BaseModel):
    """Response for subscription events"""
    subscription_events: List[SubscriptionEventItem]
    count: int


class AdminAuditLogResponse(BaseModel):
    """Audit log entry for transparency"""
    id: str
    admin_email: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
