import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from jinja2 import Template
from typing import Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[dict] = None,
    ) -> bool:
        """
        Send an email using SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML version of the email
            text_content: Plain text version (optional)
            attachments: Dict of {cid: image_path} for inline images

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("related")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Create alternative part for text/html
            msg_alternative = MIMEMultipart("alternative")
            message.attach(msg_alternative)

            # Add plain text version
            if text_content:
                part_text = MIMEText(text_content, "plain")
                msg_alternative.attach(part_text)

            # Add HTML version
            part_html = MIMEText(html_content, "html")
            msg_alternative.attach(part_html)

            # Add inline images if provided
            if attachments:
                for cid, image_path in attachments.items():
                    with open(image_path, "rb") as img_file:
                        img = MIMEImage(img_file.read())
                        img.add_header("Content-ID", f"<{cid}>")
                        img.add_header("Content-Disposition", "inline", filename=Path(image_path).name)
                        message.attach(img)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    def load_template(template_name: str, **kwargs) -> str:
        """
        Load and render an email template

        Args:
            template_name: Name of the template file (without .html)
            **kwargs: Variables to pass to the template

        Returns:
            str: Rendered HTML content
        """
        template_path = Path(__file__).parent.parent / "templates" / "emails" / f"{template_name}.html"

        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        template = Template(template_content)
        return template.render(**kwargs)

    @staticmethod
    async def send_premium_welcome_email(
        user_email: str,
        user_name: str,
        tier: str,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Send welcome email when user purchases premium

        Args:
            user_email: User's email address
            user_name: User's display name
            tier: Subscription tier (premium, premium_yearly, lifetime)
            expires_at: Expiration date (None for lifetime)

        Returns:
            bool: True if email sent successfully
        """
        try:
            # Determine subscription details
            if tier == "lifetime":
                subscription_type = "Lifetime Premium"
                expiry_text = "Your premium access never expires!"
            elif tier == "premium_yearly":
                subscription_type = "Yearly Premium"
                expiry_date = expires_at.strftime("%B %d, %Y") if expires_at else "Unknown"
                expiry_text = f"Your subscription renews on {expiry_date}"
            else:
                subscription_type = "Monthly Premium"
                expiry_date = expires_at.strftime("%B %d, %Y") if expires_at else "Unknown"
                expiry_text = f"Your subscription renews on {expiry_date}"

            # Render template
            html_content = EmailService.load_template(
                "premium_welcome",
                user_name=user_name,
                subscription_type=subscription_type,
                expiry_text=expiry_text,
                current_year=datetime.now().year,
            )

            # Get logo path
            logo_path = Path(__file__).parent.parent / "static" / "images" / "pinpoint-logo.png"

            # Send email with logo attached
            return await EmailService.send_email(
                to_email=user_email,
                subject="🎉 Welcome to Pinpoint Premium!",
                html_content=html_content,
                attachments={"logo": str(logo_path)} if logo_path.exists() else None,
            )

        except Exception as e:
            logger.error(f"❌ Failed to send premium welcome email: {str(e)}")
            return False

    @staticmethod
    async def send_subscription_expiring_email(
        user_email: str,
        user_name: str,
        days_left: int,
    ) -> bool:
        """Send email when subscription is about to expire"""
        try:
            html_content = EmailService.load_template(
                "subscription_expiring",
                user_name=user_name,
                days_left=days_left,
                current_year=datetime.now().year,
            )

            logo_path = Path(__file__).parent.parent / "static" / "images" / "pinpoint-logo.png"

            return await EmailService.send_email(
                to_email=user_email,
                subject=f"⏰ Your Pinpoint Premium expires in {days_left} days",
                html_content=html_content,
                attachments={"logo": str(logo_path)} if logo_path.exists() else None,
            )

        except Exception as e:
            logger.error(f"❌ Failed to send expiring email: {str(e)}")
            return False

    @staticmethod
    async def send_subscription_expired_email(
        user_email: str,
        user_name: str,
    ) -> bool:
        """Send email when subscription has expired"""
        try:
            html_content = EmailService.load_template(
                "subscription_expired",
                user_name=user_name,
                current_year=datetime.now().year,
            )

            logo_path = Path(__file__).parent.parent / "static" / "images" / "pinpoint-logo.png"

            return await EmailService.send_email(
                to_email=user_email,
                subject="Your Pinpoint Premium has expired",
                html_content=html_content,
                attachments={"logo": str(logo_path)} if logo_path.exists() else None,
            )

        except Exception as e:
            logger.error(f"❌ Failed to send expired email: {str(e)}")
            return False
