from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging
import hmac
import hashlib

from app.database import get_db
from app.models.user import User
from app.models.subscription import SubscriptionEvent
from app.services.email_service import EmailService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_revenuecat_signature(request_body: bytes, signature: str) -> bool:
    """
    Verify RevenueCat webhook signature

    Args:
        request_body: Raw request body bytes
        signature: Signature from X-RevenueCat-Signature header

    Returns:
        bool: True if signature is valid
    """
    # Check if webhook secret is configured
    if not settings.REVENUECAT_WEBHOOK_SECRET or settings.REVENUECAT_WEBHOOK_SECRET == "your_revenuecat_webhook_secret_here":
        logger.info("REVENUECAT_WEBHOOK_SECRET not configured, skipping signature verification (using Authorization header only)")
        return True

    try:
        # Calculate expected signature
        expected_signature = hmac.new(
            settings.REVENUECAT_WEBHOOK_SECRET.encode(),
            request_body,
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying RevenueCat signature: {str(e)}")
        return False


@router.post("/revenuecat")
async def revenuecat_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_revenuecat_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """
    Handle RevenueCat webhook events

    Event types:
    - INITIAL_PURCHASE: New subscription purchase
    - RENEWAL: Subscription renewed
    - CANCELLATION: Subscription cancelled
    - UNCANCELLATION: Subscription uncancelled
    - NON_RENEWING_PURCHASE: One-time purchase
    - EXPIRATION: Subscription expired
    - BILLING_ISSUE: Payment failed
    - PRODUCT_CHANGE: User changed subscription tier
    """
    try:
        # Verify Authorization header if configured
        if settings.REVENUECAT_WEBHOOK_AUTH_TOKEN:
            if authorization != settings.REVENUECAT_WEBHOOK_AUTH_TOKEN:
                logger.warning(f"Invalid Authorization header: {authorization}")
                raise HTTPException(status_code=401, detail="Invalid authorization")

        # Get raw request body for signature verification
        body = await request.body()

        # Verify signature if configured
        if x_revenuecat_signature:
            if not verify_revenuecat_signature(body, x_revenuecat_signature):
                logger.warning("Invalid RevenueCat webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON
        data = await request.json()

        event_type = data.get("event", {}).get("type")
        app_user_id = data.get("event", {}).get("app_user_id")  # This is our Firebase UID or email
        product_id = data.get("event", {}).get("product_id")
        subscriber_attributes = data.get("event", {}).get("subscriber_attributes", {})

        logger.info(f"📨 RevenueCat webhook received: {event_type} for user {app_user_id}")

        # Find user by Firebase UID or email
        user = db.query(User).filter(
            (User.firebase_uid == app_user_id) | (User.email == app_user_id)
        ).first()

        if not user:
            logger.warning(f"User not found for app_user_id: {app_user_id}")
            return {"status": "user_not_found", "message": "User not found but webhook acknowledged"}

        # Get user email and name
        user_email = user.email
        user_name = user.display_name or user_email.split("@")[0]

        # Handle different event types
        if event_type == "INITIAL_PURCHASE":
            await handle_initial_purchase(db, user, product_id, data, user_email, user_name)

        elif event_type == "RENEWAL":
            await handle_renewal(db, user, product_id, data)

        elif event_type == "CANCELLATION":
            await handle_cancellation(db, user, data)

        elif event_type == "EXPIRATION":
            await handle_expiration(db, user, user_email, user_name)

        elif event_type == "BILLING_ISSUE":
            await handle_billing_issue(db, user, user_email, user_name)

        elif event_type == "NON_RENEWING_PURCHASE":
            # Handle lifetime purchases
            await handle_lifetime_purchase(db, user, product_id, data, user_email, user_name)

        else:
            logger.info(f"Unhandled event type: {event_type}")

        return {"status": "success", "message": "Webhook processed successfully"}

    except Exception as e:
        logger.error(f"❌ Error processing RevenueCat webhook: {str(e)}")
        # Return 200 to prevent webhook retries for application errors
        return {"status": "error", "message": str(e)}


async def handle_initial_purchase(
    db: Session,
    user: User,
    product_id: str,
    data: dict,
    user_email: str,
    user_name: str,
):
    """Handle initial purchase event"""
    try:
        # Determine tier and expiration
        tier, expires_at = get_tier_and_expiration(product_id, data)

        # Update user subscription
        user.subscription_tier = tier
        user.subscription_expires_at = expires_at

        # Log subscription event
        subscription_event = SubscriptionEvent(
            user_id=user.id,
            event_type="purchase",
            product_id=product_id,
            platform="revenuecat",
            verified_at=datetime.utcnow(),
            expires_at=expires_at,
            raw_receipt=str(data),
        )
        db.add(subscription_event)
        db.commit()

        logger.info(f"✅ Initial purchase processed for user {user.email}: {tier}")

        # Send welcome email
        await EmailService.send_premium_welcome_email(
            user_email=user_email,
            user_name=user_name,
            tier=tier,
            expires_at=expires_at,
        )

    except Exception as e:
        logger.error(f"Error handling initial purchase: {str(e)}")
        db.rollback()


async def handle_renewal(db: Session, user: User, product_id: str, data: dict):
    """Handle subscription renewal event"""
    try:
        tier, expires_at = get_tier_and_expiration(product_id, data)

        user.subscription_tier = tier
        user.subscription_expires_at = expires_at

        subscription_event = SubscriptionEvent(
            user_id=user.id,
            event_type="renewal",
            product_id=product_id,
            platform="revenuecat",
            verified_at=datetime.utcnow(),
            expires_at=expires_at,
            raw_receipt=str(data),
        )
        db.add(subscription_event)
        db.commit()

        logger.info(f"✅ Renewal processed for user {user.email}")

    except Exception as e:
        logger.error(f"Error handling renewal: {str(e)}")
        db.rollback()


async def handle_cancellation(db: Session, user: User, data: dict):
    """Handle subscription cancellation event"""
    try:
        # User still has access until expiration
        subscription_event = SubscriptionEvent(
            user_id=user.id,
            event_type="cancellation",
            platform="revenuecat",
            verified_at=datetime.utcnow(),
            raw_receipt=str(data),
        )
        db.add(subscription_event)
        db.commit()

        logger.info(f"✅ Cancellation recorded for user {user.email}")

    except Exception as e:
        logger.error(f"Error handling cancellation: {str(e)}")
        db.rollback()


async def handle_expiration(db: Session, user: User, user_email: str, user_name: str):
    """Handle subscription expiration event"""
    try:
        user.subscription_tier = "free"
        user.subscription_expires_at = None

        db.commit()

        logger.info(f"✅ Expiration processed for user {user.email}")

        # Send expiration email
        await EmailService.send_subscription_expired_email(
            user_email=user_email,
            user_name=user_name,
        )

    except Exception as e:
        logger.error(f"Error handling expiration: {str(e)}")
        db.rollback()


async def handle_billing_issue(db: Session, user: User, user_email: str, user_name: str):
    """Handle billing issue event"""
    try:
        logger.warning(f"⚠️ Billing issue for user {user.email}")
        # Could send email notification about billing issue
    except Exception as e:
        logger.error(f"Error handling billing issue: {str(e)}")


async def handle_lifetime_purchase(
    db: Session,
    user: User,
    product_id: str,
    data: dict,
    user_email: str,
    user_name: str,
):
    """Handle lifetime purchase event"""
    try:
        user.subscription_tier = "lifetime"
        user.subscription_expires_at = None  # Lifetime = never expires

        subscription_event = SubscriptionEvent(
            user_id=user.id,
            event_type="purchase",
            product_id=product_id,
            platform="revenuecat",
            verified_at=datetime.utcnow(),
            expires_at=None,
            raw_receipt=str(data),
        )
        db.add(subscription_event)
        db.commit()

        logger.info(f"✅ Lifetime purchase processed for user {user.email}")

        # Send welcome email for lifetime
        await EmailService.send_premium_welcome_email(
            user_email=user_email,
            user_name=user_name,
            tier="lifetime",
            expires_at=None,
        )

    except Exception as e:
        logger.error(f"Error handling lifetime purchase: {str(e)}")
        db.rollback()


def get_tier_and_expiration(product_id: str, data: dict):
    """
    Determine subscription tier and expiration date from product ID

    Args:
        product_id: RevenueCat product ID
        data: Webhook data

    Returns:
        tuple: (tier, expires_at)
    """
    # Get expiration timestamp from webhook
    expiration_timestamp = data.get("event", {}).get("expiration_at_ms")

    if expiration_timestamp:
        expires_at = datetime.fromtimestamp(expiration_timestamp / 1000)
    else:
        # Default to 1 month if not provided
        expires_at = datetime.utcnow() + timedelta(days=30)

    # Determine tier based on product ID
    product_id_lower = product_id.lower() if product_id else ""

    if "yearly" in product_id_lower or "annual" in product_id_lower:
        tier = "premium_yearly"
    elif "lifetime" in product_id_lower:
        tier = "lifetime"
        expires_at = None
    else:
        tier = "premium"

    return tier, expires_at
