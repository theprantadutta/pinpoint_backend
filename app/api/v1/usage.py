"""Usage tracking and stats endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usage import (
    UsageStatsResponse,
    ReconcileUsageRequest,
    ReconcileUsageResponse,
    IncrementUsageResponse,
)
from app.services.usage_service import FREE_TIER_LIMITS
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


@router.post("/ocr", response_model=IncrementUsageResponse)
async def increment_ocr_scans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Increment the OCR scans counter for the authenticated user.

    This endpoint is called by the frontend after each successful OCR operation.
    Free users are limited to 20 OCR scans per month (resets on 1st of each month).
    Premium users have unlimited OCR scans.

    Returns the updated usage statistics for OCR scans.
    """
    usage_service = UsageService(db)

    try:
        # Increment the counter
        usage_service.increment_ocr_scans(str(current_user.id))

        # Get updated stats
        tracking = usage_service.get_or_create_usage_tracking(str(current_user.id))
        is_premium = current_user.is_premium
        limit = -1 if is_premium else FREE_TIER_LIMITS["ocr_scans_month"]
        remaining = -1 if is_premium else max(0, limit - tracking.ocr_scans_month)

        return {
            "success": True,
            "message": "OCR scan counted successfully",
            "current": tracking.ocr_scans_month,
            "limit": limit,
            "remaining": remaining,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to increment OCR scans: {str(e)}"
        )


@router.post("/export", response_model=IncrementUsageResponse)
async def increment_exports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Increment the exports counter for the authenticated user.

    This endpoint is called by the frontend after each successful export (PDF/Markdown).
    Free users are limited to 10 exports per month (resets on 1st of each month).
    Premium users have unlimited exports.

    Returns the updated usage statistics for exports.
    """
    usage_service = UsageService(db)

    try:
        # Increment the counter
        usage_service.increment_exports(str(current_user.id))

        # Get updated stats
        tracking = usage_service.get_or_create_usage_tracking(str(current_user.id))
        is_premium = current_user.is_premium
        limit = -1 if is_premium else FREE_TIER_LIMITS["exports_month"]
        remaining = -1 if is_premium else max(0, limit - tracking.exports_month)

        return {
            "success": True,
            "message": "Export counted successfully",
            "current": tracking.exports_month,
            "limit": limit,
            "remaining": remaining,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to increment exports: {str(e)}"
        )
