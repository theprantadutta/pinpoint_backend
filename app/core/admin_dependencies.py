"""Admin-specific dependencies and security"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.config import settings
from app.models.admin import AdminAuditLog
from datetime import datetime
from typing import Optional, Dict, Any

security = HTTPBearer()


async def verify_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Verify admin JWT token and email

    CRITICAL SECURITY: This function enforces multi-layer authentication:
    1. Valid JWT token structure
    2. Token hasn't expired
    3. Token has is_admin flag
    4. Email in token matches ADMIN_EMAIL from environment

    This prevents:
    - Regular users from accessing admin endpoints
    - Expired admin sessions
    - Token forgery attempts
    """
    token = credentials.credentials

    # Decode and validate JWT token
    payload = decode_access_token(token)
    if payload is None:
        # Log failed attempt
        log_admin_action(
            db=db,
            admin_email="unknown",
            action="invalid_token_attempt",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract and validate admin claims
    email: str = payload.get("email")
    is_admin: bool = payload.get("is_admin", False)

    if not email or not is_admin:
        log_admin_action(
            db=db,
            admin_email=email or "unknown",
            action="missing_admin_claims",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    # CRITICAL: Verify email matches configured admin email
    if email != settings.ADMIN_EMAIL:
        # Log unauthorized access attempt
        log_admin_action(
            db=db,
            admin_email=email,
            action="unauthorized_access_attempt",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Return verified admin data
    return {
        "email": email,
        "request": request,
        "db": db
    }


def log_admin_action(
    db: Session,
    admin_email: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None
):
    """
    Log admin action to audit trail

    This creates an immutable audit log of all admin actions for:
    - Security monitoring
    - Compliance requirements
    - Forensics in case of data breach
    - Accountability

    All admin actions MUST be logged, including:
    - Login attempts (successful and failed)
    - User data access
    - Encryption key viewing
    - Note viewing
    - Any data modifications
    """
    try:
        audit_log = AdminAuditLog(
            admin_email=admin_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        # Don't fail the request if logging fails, but log the error
        print(f"ERROR: Failed to log admin action: {e}")
        db.rollback()
