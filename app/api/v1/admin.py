"""Admin panel endpoints - HIGHLY SENSITIVE

SECURITY WARNING:
These endpoints expose user data, encryption keys, and sensitive information.
They are protected by:
1. Admin JWT tokens (1-hour expiration)
2. Email verification (must match ADMIN_EMAIL)
3. Rate limiting on authentication
4. Comprehensive audit logging

ALL access is logged for security audit.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import timedelta
from typing import Optional

from app.database import get_db
from app.config import settings
from app.core.security import create_access_token
from app.core.admin_dependencies import verify_admin_token, log_admin_action
from app.services.admin_service import AdminService
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    UserListResponse,
    UserDetailResponse,
    NoteListResponse,
    EncryptionKeyResponse,
    SyncEventsResponse,
    SubscriptionEventsResponse,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/auth", response_model=AdminLoginResponse)
@limiter.limit("5/minute")  # CRITICAL: Rate limit to prevent brute force
async def admin_login(
    request: Request,
    login_data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin password verification and JWT token generation

    SECURITY:
    - Rate limited to 5 attempts per minute per IP
    - Returns short-lived JWT (1 hour vs 7 days for regular users)
    - All attempts (success and failure) are logged
    - Token includes is_admin flag for additional verification
    """
    # Verify email matches configured admin email
    if login_data.email != settings.ADMIN_EMAIL:
        # Log failed attempt with wrong email
        log_admin_action(
            db=db,
            admin_email=login_data.email,
            action="failed_login_invalid_email",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    # Verify password matches configured admin password
    if login_data.password != settings.ADMIN_PASSWORD:
        # Log failed attempt with wrong password
        log_admin_action(
            db=db,
            admin_email=login_data.email,
            action="failed_login_invalid_password",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    # Create admin JWT token with short expiration
    token_data = {
        "email": settings.ADMIN_EMAIL,
        "is_admin": True  # Special flag for admin verification
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ADMIN_JWT_EXPIRE_MINUTES)
    )

    # Log successful login
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="successful_login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ADMIN_JWT_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin_data: dict = Depends(verify_admin_token),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
):
    """
    Get paginated list of all users

    Requires: Valid admin JWT token
    Returns: User list with basic information
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="list_users",
        ip_address=request.client.host if request.client else None,
        request_data={"page": page, "page_size": page_size, "search": search}
    )

    admin_service = AdminService(db)
    users, total = admin_service.get_users_paginated(page, page_size, search)

    total_pages = (total + page_size - 1) // page_size

    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    admin_data: dict = Depends(verify_admin_token),
):
    """
    Get detailed information about a specific user

    Requires: Valid admin JWT token
    Returns: Comprehensive user details including stats
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="view_user_details",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    admin_service = AdminService(db)
    user_data = admin_service.get_user_details(user_id)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserDetailResponse(**user_data)


@router.get("/users/{user_id}/notes", response_model=NoteListResponse)
async def get_user_notes(
    user_id: str,
    admin_data: dict = Depends(verify_admin_token),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    include_deleted: bool = Query(False, description="Include soft-deleted notes"),
):
    """
    Get user's encrypted notes

    WARNING: This exposes encrypted note data
    Requires: Valid admin JWT token
    Returns: Paginated list of encrypted notes with metadata
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action (CRITICAL: Note viewing is logged)
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="view_user_notes",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
        request_data={"page": page, "include_deleted": include_deleted}
    )

    admin_service = AdminService(db)
    notes, total = admin_service.get_user_notes_paginated(
        user_id, page, page_size, include_deleted
    )

    total_pages = (total + page_size - 1) // page_size

    return NoteListResponse(
        notes=notes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}/encryption-key", response_model=EncryptionKeyResponse)
async def get_user_encryption_key(
    user_id: str,
    admin_data: dict = Depends(verify_admin_token),
):
    """
    Get user's encryption key

    CRITICAL SECURITY WARNING:
    This endpoint returns the user's encryption key in plain text.
    With this key, ALL user notes can be decrypted.
    This is EXTREMELY SENSITIVE data.

    Use only for debugging sync issues.
    Every access is logged with IP address.

    Requires: Valid admin JWT token
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action (CRITICAL: Encryption key access is logged)
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="view_encryption_key",
        resource_type="encryption_key",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    admin_service = AdminService(db)
    key_data = admin_service.get_user_encryption_key(user_id)

    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encryption key not found for this user"
        )

    return EncryptionKeyResponse(**key_data)


@router.get("/users/{user_id}/sync-events", response_model=SyncEventsResponse)
async def get_user_sync_events(
    user_id: str,
    admin_data: dict = Depends(verify_admin_token),
    limit: int = Query(50, ge=1, le=200, description="Max events to return"),
):
    """
    Get user's sync event history

    Useful for debugging sync issues.

    Requires: Valid admin JWT token
    Returns: List of sync events with timestamps and status
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="view_sync_events",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    admin_service = AdminService(db)
    events = admin_service.get_user_sync_events(user_id, limit)

    return SyncEventsResponse(
        sync_events=events,
        count=len(events)
    )


@router.get("/users/{user_id}/subscription-events", response_model=SubscriptionEventsResponse)
async def get_user_subscription_events(
    user_id: str,
    admin_data: dict = Depends(verify_admin_token),
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
):
    """
    Get user's subscription event history

    Requires: Valid admin JWT token
    Returns: List of subscription events with verification details
    """
    db: Session = admin_data["db"]
    request: Request = admin_data["request"]

    # Log action
    log_admin_action(
        db=db,
        admin_email=settings.ADMIN_EMAIL,
        action="view_subscription_events",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    admin_service = AdminService(db)
    events = admin_service.get_user_subscription_events(user_id, limit)

    return SubscriptionEventsResponse(
        subscription_events=events,
        count=len(events)
    )
