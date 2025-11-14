"""Folder sync schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import List


class FolderSync(BaseModel):
    """Schema for syncing a single folder"""
    uuid: str  # Client-generated deterministic UUID (v5)
    title: str  # Folder name (e.g., "Random", "HomeWork")


class FolderSyncRequest(BaseModel):
    """Schema for batch folder sync request"""
    folders: List[FolderSync]


class FolderResponse(BaseModel):
    """Schema for folder response"""
    uuid: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderSyncResponse(BaseModel):
    """Schema for folder sync response"""
    folders: List[FolderResponse]
    message: str
