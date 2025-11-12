"""Admin audit logging models"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.database import Base


class AdminAuditLog(Base):
    """
    Track all admin actions for security audit

    CRITICAL: This table logs every admin action including:
    - Login attempts (successful and failed)
    - User data access
    - Encryption key access
    - Note viewing
    """

    __tablename__ = "admin_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_email = Column(String(255), nullable=False, index=True)

    # Action details
    action = Column(String(100), nullable=False)  # 'login', 'view_user', 'view_notes', etc.
    resource_type = Column(String(50), nullable=True)  # 'user', 'note', 'encryption_key'
    resource_id = Column(String(255), nullable=True)  # ID of accessed resource

    # Request details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_data = Column(JSONB, nullable=True)  # Sanitized request parameters

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AdminAuditLog(admin={self.admin_email}, action={self.action}, time={self.timestamp})>"
