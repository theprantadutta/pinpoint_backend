"""API v1 routes"""
from fastapi import APIRouter
from app.api.v1 import auth, auth_firebase, notes, folders, subscription, notifications, encryption, admin, usage, reminders, audio, webhooks

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(auth_firebase.router, prefix="/auth", tags=["authentication"])  # Firebase auth endpoints
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(encryption.router, prefix="/encryption", tags=["encryption"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
