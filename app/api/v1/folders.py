"""Folder synchronization endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.schemas.folder import (
    FolderSyncRequest,
    FolderSyncResponse,
    FolderResponse
)
from app.models.folder import Folder
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/sync", response_model=FolderSyncResponse)
async def sync_folders(
    request: FolderSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync folders between client and server

    **CRITICAL**: This endpoint should ALWAYS be called BEFORE note sync
    to ensure folders exist before notes reference them.

    Folders are NOT encrypted (non-sensitive organizational data).
    They use deterministic UUIDs (v5) based on folder name for consistency.

    The sync process:
    1. Client uploads all local folders
    2. Server upserts folders by (user_id, uuid)
    3. Server returns all user's folders
    4. Client updates local database with any new/updated folders
    """
    synced_count = 0

    # Upsert all folders from client
    for folder_data in request.folders:
        existing = db.query(Folder).filter(
            Folder.user_id == current_user.id,
            Folder.uuid == folder_data.uuid
        ).first()

        if existing:
            # Update existing folder
            existing.title = folder_data.title
            existing.updated_at = datetime.utcnow()
            synced_count += 1
        else:
            # Create new folder
            new_folder = Folder(
                user_id=current_user.id,
                uuid=folder_data.uuid,
                title=folder_data.title,
            )
            db.add(new_folder)
            synced_count += 1

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync folders: {str(e)}"
        )

    # Return all user's folders
    all_folders = db.query(Folder).filter(
        Folder.user_id == current_user.id
    ).all()

    return FolderSyncResponse(
        folders=all_folders,
        message=f"Successfully synced {synced_count} folders"
    )


@router.get("/all", response_model=List[FolderResponse])
async def get_all_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all folders for the current user

    This is a simpler endpoint for fetching folders without syncing.
    Useful for initial folder list population.
    """
    folders = db.query(Folder).filter(
        Folder.user_id == current_user.id
    ).order_by(Folder.created_at).all()

    return folders
