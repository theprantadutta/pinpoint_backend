# Email Setup Guide for Pinpoint Backend

## Overview

This guide explains how to set up email notifications for premium subscriptions in the Pinpoint backend.

## Features

✅ Welcome email when users purchase premium
✅ Beautiful HTML email templates with Pinpoint branding
✅ RevenueCat webhook integration for automatic notifications
✅ Support for all subscription tiers (Monthly, Yearly, Lifetime)
✅ Subscription expiration reminders

## Prerequisites

- Gmail account (or any SMTP-compatible email service)
- RevenueCat account with app configured
- Backend running on FastAPI

## Step 1: Gmail App Password Setup

To send emails via Gmail SMTP, you need an App Password (not your regular Gmail password).

### Creating a Gmail App Password:

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already enabled)
3. Scroll down to **App passwords**
4. Click **App passwords**
5. Select app: **Mail**
6. Select device: **Other** (enter "Pinpoint Backend")
7. Click **Generate**
8. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Update .env File:

```bash
# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=prantadutta1997@gmail.com
SMTP_PASSWORD=your_16_char_app_password_here  # Replace DUMMY_PASSWORD_REPLACE_ME with the app password
SMTP_FROM_EMAIL=prantadutta1997@gmail.com
SMTP_FROM_NAME=Prant Dutta
```

**Important**: Remove spaces from the app password. If Gmail gives you `abcd efgh ijkl mnop`, use `abcdefghijklmnop`

## Step 2: RevenueCat Webhook Setup

RevenueCat will automatically notify your backend when purchases occur.

### Configure RevenueCat Webhook:

1. Log in to [RevenueCat Dashboard](https://app.revenuecat.com/)
2. Select your app/project
3. Go to **Settings** → **Webhooks**
4. Click **Add Webhook**
5. Enter webhook URL:
   ```
   https://your-backend-domain.com/api/v1/webhooks/revenuecat
   ```
   For local testing: `https://your-ngrok-url/api/v1/webhooks/revenuecat`

6. Select events to send:
   - ✅ INITIAL_PURCHASE
   - ✅ RENEWAL
   - ✅ CANCELLATION
   - ✅ EXPIRATION
   - ✅ NON_RENEWING_PURCHASE (for lifetime)
   - ✅ BILLING_ISSUE

7. **Set Authorization Header** (Recommended for extra security):
   - In the Authorization field, enter: `Bearer Xz3aHxYNQFcdgRvb`
   - You can generate a random token: `openssl rand -hex 16`
   - This adds an extra layer beyond signature verification

8. Copy the **Webhook Secret** (looks like: `sk_abc123def456...`)

9. Add both to `.env`:
   ```bash
   REVENUECAT_WEBHOOK_SECRET=sk_abc123def456...
   REVENUECAT_WEBHOOK_AUTH_TOKEN=Bearer Xz3aHxYNQFcdgRvb
   ```

## Step 3: Install Dependencies

Install required Python packages:

```bash
cd pinpoint_backend
pip install -r requirements.txt
```

New dependencies added:
- `aiosmtplib==3.0.1` - Async SMTP client
- `python-email-validator==2.1.0` - Email validation
- `jinja2==3.1.3` - Template engine

## Step 4: Test Email Service

### Test Locally:

```python
# Create a test script: test_email.py
import asyncio
from app.services.email_service import EmailService
from datetime import datetime, timedelta

async def test_email():
    result = await EmailService.send_premium_welcome_email(
        user_email="your-test-email@gmail.com",
        user_name="Test User",
        tier="premium",
        expires_at=datetime.now() + timedelta(days=30)
    )
    print(f"Email sent: {result}")

asyncio.run(test_email())
```

Run the test:
```bash
python test_email.py
```

## Step 5: File Structure

The email system consists of these files:

```
pinpoint_backend/
├── app/
│   ├── services/
│   │   └── email_service.py          # Email sending service
│   ├── templates/
│   │   └── emails/
│   │       └── premium_welcome.html  # Email template
│   ├── static/
│   │   └── images/
│   │       └── pinpoint-logo.png     # Logo (copied from Flutter)
│   ├── api/
│   │   └── v1/
│   │       └── webhooks.py           # RevenueCat webhook handler
│   └── config.py                      # Email config added
├── .env                              # Email credentials
└── EMAIL_SETUP_GUIDE.md              # This file
```

## Step 6: How It Works

### Purchase Flow:

1. **User purchases premium in Flutter app** (via RevenueCat)
2. **RevenueCat sends webhook** to your backend (`/api/v1/webhooks/revenuecat`)
3. **Backend verifies webhook signature** (using `REVENUECAT_WEBHOOK_SECRET`)
4. **Backend updates user subscription** in database
5. **Backend sends welcome email** to user

### Email Template:

The email includes:
- ✅ Pinpoint logo (inline image)
- ✅ Welcome message with user's name
- ✅ Subscription type (Monthly/Yearly/Lifetime)
- ✅ List of all premium features
- ✅ Renewal/expiration date
- ✅ Beautiful gradient design
- ✅ Responsive mobile layout

## API Endpoints

### RevenueCat Webhook

```http
POST /api/v1/webhooks/revenuecat
Content-Type: application/json
X-RevenueCat-Signature: <webhook_signature>

{
  "event": {
    "type": "INITIAL_PURCHASE",
    "app_user_id": "user@example.com",
    "product_id": "pinpoint_premium_monthly",
    ...
  }
}
```

**Handled Events:**
- `INITIAL_PURCHASE` → Sends welcome email
- `RENEWAL` → Updates expiration date
- `CANCELLATION` → Records cancellation
- `EXPIRATION` → Sends expiration email, downgrades to free
- `NON_RENEWING_PURCHASE` → Handles lifetime purchases
- `BILLING_ISSUE` → Logs warning

## Email Templates

### Available Templates:

1. **premium_welcome.html** - Sent on new premium purchase
2. **subscription_expiring.html** - (Optional) 7 days before expiration
3. **subscription_expired.html** - (Optional) When subscription expires

### Customizing Templates:

Templates are located in `app/templates/emails/`

Variables available:
- `{{ user_name }}` - User's display name
- `{{ subscription_type }}` - "Monthly Premium", "Yearly Premium", "Lifetime Premium"
- `{{ expiry_text }}` - Human-readable expiration info
- `{{ current_year }}` - Current year for footer

## Troubleshooting

### Emails Not Sending:

**Check SMTP credentials:**
```python
# Test SMTP connection
import aiosmtplib

async def test_smtp():
    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            username="prantadutta1997@gmail.com",
            password="your_app_password",
            start_tls=True,
        )
        print("✅ SMTP connection successful")
    except Exception as e:
        print(f"❌ SMTP error: {e}")
```

**Common Issues:**
- ❌ Using regular Gmail password instead of App Password
- ❌ 2-Step Verification not enabled in Gmail
- ❌ Firewall blocking port 587
- ❌ Incorrect email in .env file

### RevenueCat Webhooks Not Received:

**Check webhook configuration:**
1. Verify webhook URL is accessible (use ngrok for local testing)
2. Check webhook logs in RevenueCat dashboard
3. Verify `REVENUECAT_WEBHOOK_SECRET` is correct
4. Check backend logs for webhook errors

**Test webhook manually:**
```bash
curl -X POST https://your-backend.com/api/v1/webhooks/revenuecat \
  -H "Content-Type: application/json" \
  -H "X-RevenueCat-Signature: test" \
  -d '{
    "event": {
      "type": "INITIAL_PURCHASE",
      "app_user_id": "test@example.com",
      "product_id": "pinpoint_premium_monthly"
    }
  }'
```

### Logo Not Showing in Email:

**Verify logo exists:**
```bash
ls app/static/images/pinpoint-logo.png
```

If missing, copy from Flutter project:
```bash
cp ../pinpoint/assets/images/pinpoint-logo.png app/static/images/
```

## Security Best Practices

1. **Never commit .env file** to Git (already in .gitignore)
2. **Use Gmail App Password**, not your main password
3. **Keep RevenueCat webhook secret private**
4. **Enable dual webhook verification** (already implemented):
   - ✅ Authorization header check (simple bearer token)
   - ✅ Webhook signature verification (HMAC-SHA256)
   - Both layers must pass for webhook to be processed
5. **Use HTTPS** in production for webhook endpoints
6. **Generate strong Authorization tokens**: Use `openssl rand -hex 16` or similar

## Production Deployment

### Environment Variables:

Set these in your production server:

```bash
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=prantadutta1997@gmail.com
SMTP_PASSWORD=<your_gmail_app_password>
SMTP_FROM_EMAIL=prantadutta1997@gmail.com
SMTP_FROM_NAME=Prant Dutta

# RevenueCat
REVENUECAT_WEBHOOK_SECRET=<your_webhook_secret>
REVENUECAT_WEBHOOK_AUTH_TOKEN=<your_authorization_token>
```

### Update RevenueCat webhook URL:

Change from ngrok URL to your production domain:
```
https://api.pinpoint.app/api/v1/webhooks/revenuecat
```

## Monitoring

### Check Email Logs:

```bash
# View backend logs
tail -f logs/app.log | grep "Email"
```

Successful email:
```
✅ Email sent successfully to user@example.com
```

Failed email:
```
❌ Failed to send email to user@example.com: [error details]
```

### Check Webhook Logs:

```bash
tail -f logs/app.log | grep "RevenueCat"
```

Expected output:
```
📨 RevenueCat webhook received: INITIAL_PURCHASE for user user@example.com
✅ Initial purchase processed for user user@example.com: premium
✅ Email sent successfully to user@example.com
```

## Support

If you encounter issues:

1. Check logs: `logs/app.log`
2. Verify .env configuration
3. Test SMTP connection manually
4. Check RevenueCat webhook logs
5. Contact: prantadutta1997@gmail.com

## License

Part of Pinpoint project - Private use only

---

**Created by:** Prant Dutta
**Last Updated:** 2025-01-11
