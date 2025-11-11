"""Encryption key management endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.note import EncryptionKey
from pydantic import BaseModel

router = APIRouter()


class EncryptionKeyRequest(BaseModel):
    """Request model for storing encryption key"""
    encryption_key: str  # Base64-encoded encryption key


class EncryptionKeyResponse(BaseModel):
    """Response model for encryption key"""
    encryption_key: str  # Base64-encoded encryption key
    updated_at: str


@router.get("/key", response_model=EncryptionKeyResponse)
async def get_encryption_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's encryption key

    Returns the user's encryption key if it exists.
    This allows the user to restore their encryption key
    after reinstalling the app or on a new device.
    """
    encryption_key = db.query(EncryptionKey).filter(
        EncryptionKey.user_id == current_user.id
    ).first()

    if not encryption_key:
        raise HTTPException(status_code=404, detail="Encryption key not found")

    return EncryptionKeyResponse(
        encryption_key=encryption_key.encryption_key,
        updated_at=encryption_key.updated_at.isoformat()
    )


@router.post("/key")
async def store_encryption_key(
    request: EncryptionKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Store or update user's encryption key

    Stores the user's encryption key on the server so it can be
    recovered after reinstalling the app or on a new device.

    SECURITY NOTE: The encryption key is stored on the server,
    which means the server CAN theoretically decrypt notes.
    This is a trade-off for allowing key recovery across devices.
    """
    # Check if key already exists
    existing_key = db.query(EncryptionKey).filter(
        EncryptionKey.user_id == current_user.id
    ).first()

    if existing_key:
        # Update existing key
        existing_key.encryption_key = request.encryption_key
        db.commit()
        db.refresh(existing_key)

        return {
            "message": "Encryption key updated successfully",
            "updated_at": existing_key.updated_at.isoformat()
        }
    else:
        # Create new key
        new_key = EncryptionKey(
            user_id=current_user.id,
            encryption_key=request.encryption_key
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        return {
            "message": "Encryption key stored successfully",
            "created_at": new_key.created_at.isoformat()
        }
