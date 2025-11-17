"""
Audio file upload/download endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path
import shutil

from app.database import get_db
from app.core.security import get_current_user

router = APIRouter()

# Audio storage directory
AUDIO_STORAGE_DIR = Path("audio_files")
AUDIO_STORAGE_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file for a voice note

    Returns the server file path that can be used to download the file
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")

        # Get file extension
        original_filename = file.filename or "audio.m4a"
        file_extension = os.path.splitext(original_filename)[1] or ".m4a"

        # Generate unique filename: user_id/uuid.extension
        user_id = current_user["user_id"]
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Create user directory
        user_dir = AUDIO_STORAGE_DIR / user_id
        user_dir.mkdir(exist_ok=True)

        # Save file
        file_path = user_dir / unique_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Return the server path (relative to audio_files directory)
        server_path = f"{user_id}/{unique_filename}"

        return {
            "success": True,
            "file_path": server_path,
            "message": "Audio file uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload audio: {str(e)}")


@router.get("/download/{user_id}/{filename}")
async def download_audio(
    user_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Download an audio file

    Only allows users to download their own audio files
    """
    try:
        # Security check: users can only download their own files
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Construct file path
        file_path = AUDIO_STORAGE_DIR / user_id / filename

        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Return file
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {str(e)}")


@router.delete("/delete/{user_id}/{filename}")
async def delete_audio(
    user_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an audio file

    Only allows users to delete their own audio files
    """
    try:
        # Security check: users can only delete their own files
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Construct file path
        file_path = AUDIO_STORAGE_DIR / user_id / filename

        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Delete file
        file_path.unlink()

        return {
            "success": True,
            "message": "Audio file deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete audio: {str(e)}")
