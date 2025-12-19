"""
Webhook endpoints for external service notifications

Handles:
- Google Play Real-Time Developer Notifications (RTDN) via Cloud Pub/Sub
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.webhook_service import WebhookService
from app.config import settings
from typing import Optional, Dict, Any
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/google-play")
async def google_play_webhook(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Google Play RTDN (Real-Time Developer Notifications) webhook endpoint

    This endpoint receives push notifications from Google Cloud Pub/Sub
    about subscription state changes.

    Configure in Google Play Console:
    1. Create a Pub/Sub topic in Google Cloud Console
    2. Create a push subscription pointing to this endpoint
    3. Set the topic name in Google Play Console > Monetization setup

    The notification payload contains subscription state changes like:
    - New purchases
    - Renewals
    - Cancellations
    - Grace periods
    - Expirations

    Returns 200 OK to acknowledge receipt (prevents Pub/Sub retries)
    """
    try:
        # Get the raw body
        body = await request.json()

        logger.info(f"Received Google Play webhook: {body.get('message', {}).get('messageId', 'no-id')}")

        # Verify the request (optional but recommended)
        # You can verify using a shared secret or Pub/Sub authentication
        verification_token = getattr(settings, 'GOOGLE_PLAY_PUBSUB_VERIFICATION_TOKEN', None)
        if verification_token:
            # Check authorization header or query param
            provided_token = request.query_params.get('token') or authorization
            if provided_token:
                # Remove "Bearer " prefix if present
                if provided_token.startswith('Bearer '):
                    provided_token = provided_token[7:]

                if not hmac.compare_digest(provided_token, verification_token):
                    logger.warning("Invalid webhook verification token")
                    raise HTTPException(status_code=401, detail="Invalid verification token")

        # Process the notification
        webhook_service = WebhookService(db)
        result = await webhook_service.process_google_play_notification(body)

        if result.get('success'):
            logger.info(f"Webhook processed successfully: {result.get('message')}")
            return {"status": "ok", "message": result.get('message')}
        else:
            # Log error but still return 200 to prevent Pub/Sub retries
            # (retrying won't fix the issue, and we don't want infinite retries)
            logger.error(f"Webhook processing error: {result.get('error')}")
            return {"status": "error", "message": result.get('error')}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook endpoint error: {e}")
        # Return 200 to acknowledge receipt even on error
        # This prevents Pub/Sub from retrying indefinitely
        return {"status": "error", "message": str(e)}


@router.post("/google-play/test")
async def test_google_play_webhook(
    db: Session = Depends(get_db)
):
    """
    Test endpoint for Google Play webhook

    Simulates a subscription renewal notification for testing purposes.
    Only available in development mode.
    """
    # Only allow in development
    if not getattr(settings, 'DEBUG', False):
        raise HTTPException(status_code=403, detail="Test endpoint only available in debug mode")

    # Simulate a test notification
    import base64
    import json

    test_notification = {
        "testNotification": {
            "version": "1.0"
        }
    }

    encoded_data = base64.b64encode(json.dumps(test_notification).encode()).decode()

    test_message = {
        "message": {
            "data": encoded_data,
            "messageId": "test-message-123",
            "publishTime": "2025-12-19T00:00:00Z"
        }
    }

    webhook_service = WebhookService(db)
    result = await webhook_service.process_google_play_notification(test_message)

    return {
        "status": "test",
        "result": result,
        "note": "This is a test endpoint. Configure real webhooks in Google Play Console."
    }


@router.get("/health")
async def webhook_health():
    """
    Health check for webhook endpoints

    Used by monitoring systems to verify the webhook service is running.
    """
    return {
        "status": "healthy",
        "service": "webhooks",
        "google_play_configured": bool(getattr(settings, 'GOOGLE_PLAY_PUBSUB_VERIFICATION_TOKEN', None))
    }
