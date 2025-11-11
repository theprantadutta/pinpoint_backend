"""Subscription and payment endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.subscription import (
    GooglePlayPurchaseVerify,
    DeviceBasedPurchaseVerify,
    SubscriptionStatusResponse,
    PurchaseVerificationResponse,
    RevenueCatSyncRequest
)
from app.services.payment_service import PaymentService
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.subscription import SubscriptionEvent
from app.services.email_service import EmailService
from datetime import datetime
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


# ============================================================================
# RevenueCat Client-Side Sync Endpoint
# ============================================================================

@router.post("/sync-revenuecat", response_model=PurchaseVerificationResponse)
async def sync_revenuecat_purchase(
    sync_data: RevenueCatSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync RevenueCat purchase status from client side

    This provides client-side redundancy in addition to RevenueCat webhooks.
    If webhooks fail, this ensures the backend stays in sync.

    - **firebase_uid**: User's Firebase UID (optional, provide either this or email)
    - **email**: User's email (optional, provide either this or firebase_uid)
    - **product_id**: RevenueCat product ID
    - **is_premium**: Whether user has active premium entitlement
    - **expires_at**: Expiration date (None for lifetime)

    Returns subscription status after sync
    """
    try:
        # Find user by Firebase UID or email
        if not sync_data.firebase_uid and not sync_data.email:
            raise HTTPException(
                status_code=400,
                detail="Either firebase_uid or email must be provided"
            )

        query = db.query(User)
        if sync_data.firebase_uid:
            query = query.filter(User.firebase_uid == sync_data.firebase_uid)
        else:
            query = query.filter(User.email == sync_data.email)

        user = query.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Determine tier based on product ID
        product_id_lower = sync_data.product_id.lower() if sync_data.product_id else ""

        if not sync_data.is_premium:
            tier = "free"
            expires_at = None
        elif "yearly" in product_id_lower or "annual" in product_id_lower:
            tier = "premium_yearly"
            expires_at = sync_data.expires_at
        elif "lifetime" in product_id_lower:
            tier = "lifetime"
            expires_at = None
        else:
            tier = "premium"
            expires_at = sync_data.expires_at

        # Check if this is a new purchase (user was not premium before)
        was_premium = user.subscription_tier not in ["free", None]
        is_new_purchase = not was_premium and sync_data.is_premium

        # Update user subscription
        user.subscription_tier = tier
        user.subscription_expires_at = expires_at

        # Log subscription event
        subscription_event = SubscriptionEvent(
            user_id=user.id,
            event_type="client_sync",
            product_id=sync_data.product_id,
            platform="revenuecat_client",
            verified_at=datetime.utcnow(),
            expires_at=expires_at,
            raw_receipt=f"Client sync: {sync_data.model_dump_json()}",
        )
        db.add(subscription_event)
        db.commit()

        logger.info(f"✅ RevenueCat client sync for user {user.email}: {tier}")

        # Send welcome email for new purchases
        if is_new_purchase:
            user_name = user.display_name or user.email.split("@")[0]
            await EmailService.send_premium_welcome_email(
                user_email=user.email,
                user_name=user_name,
                tier=tier,
                expires_at=expires_at,
            )
            logger.info(f"📧 Welcome email sent to {user.email}")

        return PurchaseVerificationResponse(
            success=True,
            tier=tier,
            expires_at=expires_at,
            message="Subscription synced successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing RevenueCat purchase: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync purchase: {str(e)}"
        )
