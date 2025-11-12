"""Usage tracking and stats endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usage import (
    UsageStatsResponse,
    ReconcileUsageRequest,
    ReconcileUsageResponse,
)
from app.services.usage_service import UsageService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current usage statistics for the authenticated user.

    Returns comprehensive usage data including:
    - Synced notes count (permanent counter)
    - OCR scans this month (resets monthly)
    - Exports this month (resets monthly)
    - Remaining quotas for each feature
    - Premium status

    This endpoint is called by the frontend to:
    - Display usage in settings/account screen
    - Show usage in create note menu
    - Reconcile usage after sync operations
    """
    usage_service = UsageService(db)

    try:
        stats = usage_service.get_user_usage(str(current_user.id))
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage stats: {str(e)}"
        )


@router.post("/reconcile", response_model=ReconcileUsageResponse)
async def reconcile_usage(
    request: ReconcileUsageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reconcile synced notes count with actual database count.

    This endpoint:
    - Counts actual non-deleted notes in database
    - Updates the usage tracking counter to match
    - Returns the old and new counts

    Useful for:
    - Fixing discrepancies between counter and reality
    - Initial migration of existing users
    - Manual reconciliation when issues are detected
    """
    usage_service = UsageService(db)

    try:
        # Get current count before reconciliation
        tracking = usage_service.get_or_create_usage_tracking(str(current_user.id))
        old_count = tracking.synced_notes_count

        # Reconcile with actual database count
        new_count = usage_service.reconcile_synced_notes_count(str(current_user.id))

        reconciled = (old_count != new_count)

        return {
            "success": True,
            "message": f"Reconciliation complete. Updated from {old_count} to {new_count} notes.",
            "old_count": old_count,
            "new_count": new_count,
            "reconciled": reconciled,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reconcile usage: {str(e)}"
        )
