"""Subscription and payment endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.subscription import (
    GooglePlayPurchaseVerify,
    DeviceBasedPurchaseVerify,
    SubscriptionStatusResponse,
    PurchaseVerificationResponse
)
from app.services.payment_service import PaymentService
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.subscription import SubscriptionEvent
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/verify", response_model=PurchaseVerificationResponse)
async def verify_purchase(
    purchase_data: GooglePlayPurchaseVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify Google Play purchase

    - **purchase_token**: Google Play purchase token
    - **product_id**: Product ID (e.g., 'pinpoint_premium_monthly')

    Returns subscription status after verification
    """
    payment_service = PaymentService(db)

    result = await payment_service.verify_google_play_purchase(
        user_id=str(current_user.id),
        purchase_token=purchase_data.purchase_token,
        product_id=purchase_data.product_id
    )

    return result


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription status

    Returns whether user has premium access and expiration date
    """
    payment_service = PaymentService(db)

    status = payment_service.get_subscription_status(str(current_user.id))

    return status


# ============================================================================
# Device-Based Subscription Endpoints (No Authentication Required)
# ============================================================================

@router.post("/verify-device", response_model=PurchaseVerificationResponse)
async def verify_device_purchase(
    purchase_data: DeviceBasedPurchaseVerify,
    db: Session = Depends(get_db)
):
    """
    Verify Google Play purchase using device ID (no authentication required)

    - **device_id**: Unique device identifier
    - **purchase_token**: Google Play purchase token
    - **product_id**: Product ID (e.g., 'pinpoint_premium_monthly')
    - **user_id**: Optional user ID to sync subscription with user account

    Returns subscription status after verification
    """
    payment_service = PaymentService(db)

    # Get or create device
    device = db.query(Device).filter(Device.device_id == purchase_data.device_id).first()
    if not device:
        device = Device(device_id=purchase_data.device_id)
        db.add(device)
        db.commit()
        db.refresh(device)

    # Verify purchase with Google Play (and optionally sync with user)
    result = await payment_service.verify_google_play_purchase_for_device(
        device_id=purchase_data.device_id,
        purchase_token=purchase_data.purchase_token,
        product_id=purchase_data.product_id,
        user_id=purchase_data.user_id  # Pass user_id for syncing
    )

    return result


def _extract_subscription_type(product_id: str) -> str:
    """Extract subscription type from product ID"""
    if not product_id:
        return "free"
    if "lifetime" in product_id:
        return "lifetime"
    elif "yearly" in product_id:
        return "yearly"
    elif "monthly" in product_id:
        return "monthly"
    return "unknown"


@router.get("/status/{device_id}", response_model=SubscriptionStatusResponse)
async def get_device_subscription_status(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Get subscription status by device ID (no authentication required)

    Returns complete subscription status including:
    - is_premium: Whether device has active premium access
    - tier: Subscription tier ('free', 'premium')
    - expires_at: When subscription expires
    - product_id: Product ID of current subscription
    - is_in_grace_period: Whether device is in payment grace period
    - grace_period_ends_at: When grace period ends
    - subscription_status: Detailed status ('active', 'grace_period', 'expired', 'free')
    - subscription_type: Type of subscription ('monthly', 'yearly', 'lifetime')
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        return SubscriptionStatusResponse(
            is_premium=False,
            tier="free",
            expires_at=None,
            product_id=None,
            is_in_grace_period=False,
            grace_period_ends_at=None,
            subscription_status="free",
            subscription_type="free"
        )

    # Check if subscription expired (but not in grace period)
    if (device.subscription_expires_at and
        device.subscription_expires_at < datetime.utcnow() and
        not device.is_in_grace_period()):
        # Only reset to free if not in grace period
        device.subscription_tier = "free"
        db.commit()

    return SubscriptionStatusResponse(
        is_premium=device.is_premium,
        tier=device.subscription_tier,
        expires_at=device.subscription_expires_at,
        product_id=device.subscription_product_id,
        is_in_grace_period=device.is_in_grace_period(),
        grace_period_ends_at=device.grace_period_ends_at,
        subscription_status=device.get_subscription_status(),
        subscription_type=_extract_subscription_type(device.subscription_product_id)
    )
