"""Subscription and payment endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.subscription import (
    GooglePlayPurchaseVerify,
    SubscriptionStatusResponse,
    PurchaseVerificationResponse
)
from app.services.payment_service import PaymentService
from app.core.dependencies import get_current_user
from app.models.user import User

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
