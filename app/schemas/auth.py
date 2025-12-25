"""Authentication schemas"""
from pydantic import BaseModel, UUID4
from typing import Optional


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user_id: str


class TokenData(BaseModel):
    """Token payload data"""
    user_id: UUID4


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh"""
    refresh_token: str
