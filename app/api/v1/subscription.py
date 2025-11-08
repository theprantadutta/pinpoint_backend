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
from datetime import datetime

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

    # Verify purchase with Google Play
    result = await payment_service.verify_google_play_purchase_for_device(
        device_id=purchase_data.device_id,
        purchase_token=purchase_data.purchase_token,
        product_id=purchase_data.product_id
    )

    return result


@router.get("/status/{device_id}", response_model=SubscriptionStatusResponse)
async def get_device_subscription_status(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Get subscription status by device ID (no authentication required)

    Returns whether device has premium access and expiration date
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        return SubscriptionStatusResponse(
            is_premium=False,
            tier="free",
            expires_at=None
        )

    # Check if subscription expired
    if device.subscription_expires_at and device.subscription_expires_at < datetime.utcnow():
        device.subscription_tier = "free"
        db.commit()

    return SubscriptionStatusResponse(
        is_premium=device.is_premium,
        tier=device.subscription_tier,
        expires_at=device.subscription_expires_at
    )
