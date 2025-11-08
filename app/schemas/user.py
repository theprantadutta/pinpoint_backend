"""User schemas"""
from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str


class UserLogin(UserBase):
    """Schema for user login"""
    password: str


class UserResponse(UserBase):
    """Schema for user response (no password)"""
    id: UUID4
    created_at: datetime
    subscription_tier: str
    is_active: bool
    is_premium: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
