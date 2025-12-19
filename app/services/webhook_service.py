"""
Google Play Real-Time Developer Notifications (RTDN) Webhook Service

Handles subscription state changes from Google Play:
- SUBSCRIPTION_PURCHASED: New subscription purchased
- SUBSCRIPTION_RENEWED: Subscription renewed successfully
- SUBSCRIPTION_RECOVERED: Recovered from grace period/account hold
- SUBSCRIPTION_CANCELED: User canceled subscription
- SUBSCRIPTION_ON_HOLD: Payment failed, subscription on hold
- SUBSCRIPTION_IN_GRACE_PERIOD: Payment failed but in grace period
- SUBSCRIPTION_EXPIRED: Subscription expired
- SUBSCRIPTION_REVOKED: Subscription revoked (refund, etc.)
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.device import Device
from app.models.user import User
from app.models.subscription import SubscriptionEvent
from app.config import settings
from app.services.notification_service import NotificationService
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import base64
import json
import logging

logger = logging.getLogger(__name__)


# Google Play subscription notification types
# See: https://developer.android.com/google/play/billing/rtdn-reference
class SubscriptionNotificationType:
    SUBSCRIPTION_RECOVERED = 1
    SUBSCRIPTION_RENEWED = 2
    SUBSCRIPTION_CANCELED = 3
    SUBSCRIPTION_PURCHASED = 4
    SUBSCRIPTION_ON_HOLD = 5
    SUBSCRIPTION_IN_GRACE_PERIOD = 6
    SUBSCRIPTION_RESTARTED = 7
    SUBSCRIPTION_PRICE_CHANGE_CONFIRMED = 8
    SUBSCRIPTION_DEFERRED = 9
    SUBSCRIPTION_PAUSED = 10
    SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED = 11
    SUBSCRIPTION_REVOKED = 12
    SUBSCRIPTION_EXPIRED = 13


class WebhookService:
    """Service for handling Google Play RTDN webhooks"""

    def __init__(self, db: Session):
        self.db = db

    async def process_google_play_notification(self, message_data: Dict[str, Any]) -> Dict:
        """
        Process a Google Play RTDN notification from Pub/Sub

        The message_data should contain the Pub/Sub message with:
        - message.data: Base64-encoded notification payload
        - message.messageId: Unique message ID
        - message.publishTime: When the message was published

        Args:
            message_data: The Pub/Sub push message

        Returns:
            Dict with processing result
        """
        try:
            # Extract and decode the notification data
            message = message_data.get('message', {})
            encoded_data = message.get('data', '')

            if not encoded_data:
                logger.warning("Empty notification data received")
                return {"success": False, "error": "Empty notification data"}

            # Decode base64 data
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            notification = json.loads(decoded_data)

            logger.info(f"Processing Google Play notification: {json.dumps(notification, default=str)}")

            # Extract subscription notification
            subscription_notification = notification.get('subscriptionNotification', {})
            if not subscription_notification:
                # This might be a test notification or other type
                test_notification = notification.get('testNotification')
                if test_notification:
                    logger.info("Received test notification - acknowledged")
                    return {"success": True, "message": "Test notification acknowledged"}

                logger.warning(f"Unknown notification type: {notification}")
                return {"success": True, "message": "Unknown notification type, ignored"}

            # Get notification details
            notification_type = subscription_notification.get('notificationType')
            purchase_token = subscription_notification.get('purchaseToken')
            subscription_id = subscription_notification.get('subscriptionId')

            if not purchase_token:
                logger.warning("No purchase token in notification")
                return {"success": False, "error": "No purchase token"}

            # Handle the notification based on type
            return await self._handle_subscription_notification(
                notification_type=notification_type,
                purchase_token=purchase_token,
                subscription_id=subscription_id
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode notification JSON: {e}")
            return {"success": False, "error": f"JSON decode error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_subscription_notification(
        self,
        notification_type: int,
        purchase_token: str,
        subscription_id: str
    ) -> Dict:
        """
        Handle a subscription notification based on its type

        Args:
            notification_type: Type of notification (see SubscriptionNotificationType)
            purchase_token: Google Play purchase token
            subscription_id: Subscription product ID

        Returns:
            Dict with handling result
        """
        # Find device by purchase token
        device = self.db.query(Device).filter(
            Device.last_purchase_token == purchase_token
        ).first()

        # Find user by purchase token
        user = self.db.query(User).filter(
            User.google_play_purchase_token == purchase_token
        ).first()

        if not device and not user:
            logger.warning(f"No device or user found for purchase token: {purchase_token[:20]}...")
            # Still return success to acknowledge the notification
            return {"success": True, "message": "No matching device/user found, notification ignored"}

        event_type = self._get_event_type_name(notification_type)
        logger.info(f"Handling {event_type} for device={device.device_id if device else None}, user={user.id if user else None}")

        # Route to appropriate handler
        if notification_type == SubscriptionNotificationType.SUBSCRIPTION_PURCHASED:
            return await self._handle_purchase(device, user, subscription_id, purchase_token)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_RENEWED:
            return await self._handle_renewal(device, user, subscription_id)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_RECOVERED:
            return await self._handle_recovery(device, user, subscription_id)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_CANCELED:
            return await self._handle_cancellation(device, user)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_ON_HOLD:
            return await self._handle_on_hold(device, user)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_IN_GRACE_PERIOD:
            return await self._handle_grace_period(device, user)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_EXPIRED:
            return await self._handle_expiration(device, user)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_REVOKED:
            return await self._handle_revocation(device, user)

        elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_RESTARTED:
            return await self._handle_restart(device, user, subscription_id)

        else:
            logger.info(f"Unhandled notification type: {notification_type}")
            return {"success": True, "message": f"Notification type {notification_type} not handled"}

    async def _handle_purchase(
        self,
        device: Optional[Device],
        user: Optional[User],
        subscription_id: str,
        purchase_token: str
    ) -> Dict:
        """Handle new subscription purchase"""
        # This is usually handled by the verify endpoint, but we can update here too
        if device:
            device.subscription_tier = 'premium'
            device.subscription_product_id = subscription_id
            device.last_purchase_token = purchase_token
            device.clear_grace_period()

        if user:
            user.subscription_tier = 'premium'
            user.google_play_purchase_token = purchase_token
            user.grace_period_ends_at = None

        self._log_event(user, 'purchase_webhook', subscription_id)
        self.db.commit()

        return {"success": True, "message": "Purchase notification processed"}

    async def _handle_renewal(
        self,
        device: Optional[Device],
        user: Optional[User],
        subscription_id: str
    ) -> Dict:
        """Handle subscription renewal"""
        # Calculate new expiration based on product
        new_expiry = self._calculate_expiry(subscription_id)

        if device:
            device.subscription_expires_at = new_expiry
            device.clear_grace_period()

        if user:
            user.subscription_expires_at = new_expiry
            user.grace_period_ends_at = None

        self._log_event(user, 'renewal', subscription_id)
        self.db.commit()

        logger.info(f"Subscription renewed until {new_expiry}")
        return {"success": True, "message": "Renewal processed"}

    async def _handle_recovery(
        self,
        device: Optional[Device],
        user: Optional[User],
        subscription_id: str
    ) -> Dict:
        """Handle recovery from grace period/hold"""
        new_expiry = self._calculate_expiry(subscription_id)

        if device:
            device.subscription_tier = 'premium'
            device.subscription_expires_at = new_expiry
            device.clear_grace_period()

        if user:
            user.subscription_tier = 'premium'
            user.subscription_expires_at = new_expiry
            user.grace_period_ends_at = None

        self._log_event(user, 'recovery', subscription_id)
        self.db.commit()

        logger.info("Subscription recovered from grace period")
        return {"success": True, "message": "Recovery processed"}

    async def _handle_cancellation(
        self,
        device: Optional[Device],
        user: Optional[User]
    ) -> Dict:
        """Handle subscription cancellation (user canceled, will expire at end of period)"""
        # Note: User still has access until expiration, just mark that renewal won't happen
        self._log_event(user, 'cancellation', None)
        self.db.commit()

        logger.info("Subscription canceled (will expire at end of billing period)")
        return {"success": True, "message": "Cancellation recorded"}

    async def _handle_on_hold(
        self,
        device: Optional[Device],
        user: Optional[User]
    ) -> Dict:
        """Handle subscription on hold (payment failed severely)"""
        # Start grace period
        grace_days = getattr(settings, 'GRACE_PERIOD_DAYS', 3)

        if device:
            device.start_grace_period(grace_days)

        if user:
            user.start_grace_period(grace_days)
            # Send push notification
            await self._send_payment_failure_notification(user)

        self._log_event(user, 'on_hold', None)
        self.db.commit()

        logger.info(f"Subscription on hold, grace period started ({grace_days} days)")
        return {"success": True, "message": "On-hold processed, grace period started"}

    async def _handle_grace_period(
        self,
        device: Optional[Device],
        user: Optional[User]
    ) -> Dict:
        """Handle subscription entering grace period (payment failed but retrying)"""
        grace_days = getattr(settings, 'GRACE_PERIOD_DAYS', 3)

        if device:
            device.start_grace_period(grace_days)

        if user:
            user.start_grace_period(grace_days)
            # Send push notification
            await self._send_payment_failure_notification(user)

        self._log_event(user, 'grace_period', None)
        self.db.commit()

        logger.info(f"Subscription in grace period ({grace_days} days)")
        return {"success": True, "message": "Grace period started"}

    async def _handle_expiration(
        self,
        device: Optional[Device],
        user: Optional[User]
    ) -> Dict:
        """Handle subscription expiration"""
        if device:
            device.subscription_tier = 'free'
            device.grace_period_ends_at = None

        if user:
            user.subscription_tier = 'free'
            user.grace_period_ends_at = None

        self._log_event(user, 'expiration', None)
        self.db.commit()

        logger.info("Subscription expired")
        return {"success": True, "message": "Expiration processed"}

    async def _handle_revocation(
        self,
        device: Optional[Device],
        user: Optional[User]
    ) -> Dict:
        """Handle subscription revocation (refund, abuse, etc.)"""
        if device:
            device.subscription_tier = 'free'
            device.subscription_expires_at = None
            device.grace_period_ends_at = None

        if user:
            user.subscription_tier = 'free'
            user.subscription_expires_at = None
            user.grace_period_ends_at = None

        self._log_event(user, 'revocation', None)
        self.db.commit()

        logger.info("Subscription revoked")
        return {"success": True, "message": "Revocation processed"}

    async def _handle_restart(
        self,
        device: Optional[Device],
        user: Optional[User],
        subscription_id: str
    ) -> Dict:
        """Handle subscription restart (user re-subscribed)"""
        new_expiry = self._calculate_expiry(subscription_id)

        if device:
            device.subscription_tier = 'premium'
            device.subscription_expires_at = new_expiry
            device.clear_grace_period()

        if user:
            user.subscription_tier = 'premium'
            user.subscription_expires_at = new_expiry
            user.grace_period_ends_at = None

        self._log_event(user, 'restart', subscription_id)
        self.db.commit()

        logger.info("Subscription restarted")
        return {"success": True, "message": "Restart processed"}

    def _calculate_expiry(self, subscription_id: str) -> Optional[datetime]:
        """Calculate subscription expiry based on product ID"""
        if not subscription_id:
            return datetime.utcnow() + timedelta(days=30)

        if 'lifetime' in subscription_id:
            return None  # No expiry
        elif 'yearly' in subscription_id:
            return datetime.utcnow() + timedelta(days=365)
        elif 'monthly' in subscription_id:
            return datetime.utcnow() + timedelta(days=30)
        else:
            return datetime.utcnow() + timedelta(days=30)

    def _log_event(
        self,
        user: Optional[User],
        event_type: str,
        product_id: Optional[str]
    ) -> None:
        """Log a subscription event"""
        event = SubscriptionEvent(
            user_id=str(user.id) if user else None,
            event_type=event_type,
            product_id=product_id,
            platform='android',
            raw_receipt=f'RTDN_WEBHOOK_{event_type.upper()}'
        )
        self.db.add(event)

    async def _send_payment_failure_notification(self, user: User) -> None:
        """Send push notification about payment failure"""
        try:
            notification_service = NotificationService(self.db)
            await notification_service.send_notification_to_user(
                user_id=str(user.id),
                title="Payment Failed",
                body="Your payment failed. Please update your payment method within 3 days to keep premium access.",
                data={"type": "payment_failure", "action": "open_subscription"}
            )
            logger.info(f"Sent payment failure notification to user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send payment failure notification: {e}")

    def _get_event_type_name(self, notification_type: int) -> str:
        """Get human-readable name for notification type"""
        names = {
            1: "SUBSCRIPTION_RECOVERED",
            2: "SUBSCRIPTION_RENEWED",
            3: "SUBSCRIPTION_CANCELED",
            4: "SUBSCRIPTION_PURCHASED",
            5: "SUBSCRIPTION_ON_HOLD",
            6: "SUBSCRIPTION_IN_GRACE_PERIOD",
            7: "SUBSCRIPTION_RESTARTED",
            8: "SUBSCRIPTION_PRICE_CHANGE_CONFIRMED",
            9: "SUBSCRIPTION_DEFERRED",
            10: "SUBSCRIPTION_PAUSED",
            11: "SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED",
            12: "SUBSCRIPTION_REVOKED",
            13: "SUBSCRIPTION_EXPIRED",
        }
        return names.get(notification_type, f"UNKNOWN_{notification_type}")
