# Google Play Console Setup Guide for Pinpoint

This guide will help you configure your Google Play Console subscriptions and integrate them with your Pinpoint app.

---

## Table of Contents

1. [Product Configuration](#product-configuration)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Service Account Configuration](#service-account-configuration)
4. [Real-time Developer Notifications](#real-time-developer-notifications-recommended)
5. [Testing](#testing)
6. [Backend Configuration](#backend-configuration)

---

## Product Configuration

Configure these three subscription/product items in Google Play Console:

### 1. Monthly Subscription

**Product Details:**
- **Product ID**: `pinpoint_premium_monthly`
- **Product Type**: Auto-renewable subscription
- **Base Plan Name**: Monthly Premium
- **Billing Period**: Every 1 month
- **Price**: **$4.99 USD/month**

**Free Trial Configuration:**
- **Enable Free Trial**: Yes
- **Trial Duration**: **7 days**
- **Trial Eligibility**: New subscribers only
- **What happens after trial**: Automatically converts to paid subscription

**Grace Period (Account Hold):**
- **Enable Account Hold**: Yes
- **Duration**: **3 days**
- **Payment Retry Schedule**: Retry every 24 hours during grace period

**Configuration Steps:**
1. Go to Google Play Console > Your App > Monetize > Subscriptions
2. Click "Create subscription"
3. Enter product ID: `pinpoint_premium_monthly`
4. Add base plan with monthly billing
5. Set price to $4.99 USD (add other countries as needed)
6. Under "Free Trial", enable and set to 7 days
7. Under "Grace period", enable Account Hold for 3 days
8. Save and activate

---

### 2. Yearly Subscription

**Product Details:**
- **Product ID**: `pinpoint_premium_yearly`
- **Product Type**: Auto-renewable subscription
- **Base Plan Name**: Annual Premium
- **Billing Period**: Every 12 months
- **Price**: **$39.99 USD/year** (33% savings vs monthly)

**Free Trial Configuration:**
- **Enable Free Trial**: Yes
- **Trial Duration**: **7 days**
- **Trial Eligibility**: New subscribers only
- **What happens after trial**: Automatically converts to paid subscription

**Grace Period (Account Hold):**
- **Enable Account Hold**: Yes
- **Duration**: **3 days**
- **Payment Retry Schedule**: Retry every 24 hours during grace period

**Configuration Steps:**
1. Go to Google Play Console > Your App > Monetize > Subscriptions
2. Click "Create subscription"
3. Enter product ID: `pinpoint_premium_yearly`
4. Add base plan with annual billing (12 months)
5. Set price to $49.99 USD (add other countries as needed)
6. Under "Free Trial", enable and set to 7 days
7. Under "Grace period", enable Account Hold for 3 days
8. Save and activate

---

### 3. Lifetime Purchase

**Product Details:**
- **Product ID**: `pinpoint_premium_lifetime`
- **Product Type**: One-time product (in-app product)
- **Price**: **$99.99 USD** (one-time payment)
- **Product Name**: Lifetime Premium Access
- **Description**: One-time payment for lifetime access to all premium features

**Configuration Steps:**
1. Go to Google Play Console > Your App > Monetize > In-app products
2. Click "Create product"
3. Enter product ID: `pinpoint_premium_lifetime`
4. Select "One-time product"
5. Set price to $199.99 USD (add other countries as needed)
6. Add description and title
7. Save and activate

**Note**: Lifetime purchases do not have trials or grace periods.

---

## Google Cloud Setup

### Prerequisites
- Google Cloud Console account (console.cloud.google.com)
- Google Play Console account with app published or in testing

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" > "New Project"
3. Name it "Pinpoint Subscriptions" (or your preferred name)
4. Click "Create"
5. Note the **Project ID** - you'll need this

### Step 2: Enable Google Play Developer API

1. In Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Play Developer API"
3. Click on it and click "Enable"
4. Wait for activation (may take a few minutes)

---

## Service Account Configuration

### Step 1: Create Service Account

1. In Google Cloud Console, go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. **Service Account Details:**
   - Name: `pinpoint-play-billing`
   - Description: "Service account for Pinpoint Google Play billing verification"
4. Click "Create and Continue"

### Step 2: Grant Permissions (Skip for now)

- Click "Continue" without adding roles (permissions will be granted in Play Console)
- Click "Done"

### Step 3: Create JSON Key

1. Click on the newly created service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. **Save the downloaded JSON file securely** - you'll need this for your backend
7. Rename it to something like `google-play-service-account.json`

### Step 4: Link Service Account to Google Play Console

1. Go to [Google Play Console](https://play.google.com/console)
2. Go to "Users and permissions"
3. Click "Invite new users"
4. **Enter the service account email** (e.g., `pinpoint-play-billing@your-project.iam.gserviceaccount.com`)
5. Grant the following permissions:
   - **Financial data**: View
   - **Orders and subscriptions**: View
6. Click "Invite user"
7. Accept the invitation (check the service account email if needed)

**Important**: It may take up to 24 hours for permissions to fully propagate.

---

## Real-time Developer Notifications (Recommended)

Real-time Developer Notifications (RTDN) allow your backend to automatically detect subscription changes (renewals, cancellations, payment failures) and trigger grace periods automatically.

### Step 1: Create Pub/Sub Topic

1. In Google Cloud Console, go to "Pub/Sub" > "Topics"
2. Click "Create Topic"
3. **Topic ID**: `pinpoint-play-notifications`
4. Leave other settings as default
5. Click "Create"
6. Note the full topic name (e.g., `projects/your-project/topics/pinpoint-play-notifications`)

### Step 2: Grant Publish Permission to Google Play

1. Click on your new topic
2. Go to "Permissions" tab
3. Click "Add Principal"
4. **Principal**: `google-play-developer-notifications@system.gserviceaccount.com`
5. **Role**: `Pub/Sub Publisher`
6. Click "Save"

### Step 3: Configure in Google Play Console

1. Go to Google Play Console > Your App > Monetize > Monetization setup
2. Under "Real-time developer notifications", click "Edit"
3. **Topic name**: Enter the full topic name from Step 1
4. Click "Save"

### Step 4: Create Backend Webhook (Optional - for advanced users)

If you want automatic grace period handling, you'll need to create a webhook endpoint that subscribes to this Pub/Sub topic. This is optional as the app also handles subscription status checking.

**Example endpoint:** `POST /webhooks/google-play`

---

## Testing

### Test Accounts

1. Go to Google Play Console > Your App > Testing > License testing
2. Add test Gmail accounts
3. These accounts can make test purchases without being charged

### Test Purchase Flow

1. Build and install the app on a test device
2. Sign in with a test account
3. Navigate to subscription screen
4. Purchase a subscription
5. Verify:
   - 7-day trial starts
   - Premium features unlock
   - Backend receives purchase verification
   - Subscription appears in Google Play account

### Test Grace Period

1. Let subscription expire or fail payment (use test cards)
2. Verify 3-day grace period activates
3. Verify premium access continues during grace period
4. Verify user sees grace period warning in app

---

## Backend Configuration

### Step 1: Add Service Account JSON to Backend

1. Copy the `google-play-service-account.json` file to your backend server
2. Store it securely (e.g., `/opt/pinpoint/credentials/google-play-service-account.json`)
3. **Never commit this file to version control!**

### Step 2: Update Environment Variables

Edit your `.env` file on the backend:

```env
# Google Play Billing
GOOGLE_PLAY_SERVICE_ACCOUNT_PATH=/path/to/google-play-service-account.json
GOOGLE_PLAY_PACKAGE_NAME=com.pinpoint.app

# Subscription Settings
GRACE_PERIOD_DAYS=3
TRIAL_PERIOD_DAYS=7
```

### Step 3: Verify Backend Setup

Test the backend integration:

```bash
# Test purchase verification endpoint
curl -X POST https://your-backend.com/api/v1/subscription/verify \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purchase_token": "test_purchase_token",
    "product_id": "pinpoint_premium_monthly"
  }'
```

Expected response:
```json
{
  "success": true,
  "tier": "premium",
  "expires_at": "2025-12-11T00:00:00Z",
  "is_in_grace_period": false,
  "message": "Purchase verified successfully"
}
```

### Step 4: Run Database Migration

Apply the grace period database migration:

```bash
cd /path/to/pinpoint_backend
alembic upgrade head
```

This adds the `grace_period_ends_at` column to the users table.

---

## Pricing Summary

| Product | Type | Price | Trial | Grace Period |
|---------|------|-------|-------|--------------|
| Monthly | Subscription | $4.99/month | 7 days | 3 days |
| Yearly | Subscription | $39.99/year | 7 days | 3 days |
| Lifetime | One-time | $99.99 | No | No |

**Savings:**
- Yearly vs Monthly: Save **$19.89** (33% discount)
- Lifetime vs 3 years monthly: Save **$79.65**

---

## Troubleshooting

### "Service account doesn't have required permissions"

- Wait up to 24 hours for permissions to propagate
- Verify service account has "View financial data" permission in Play Console
- Ensure API is enabled in Google Cloud Console

### "Invalid purchase token"

- Check that product IDs match exactly: `pinpoint_premium_monthly`, `pinpoint_premium_yearly`, `pinpoint_premium_lifetime`
- Verify you're using the correct environment (test vs production)
- Ensure purchase was made in the correct app (check package name)

### "Grace period not activating"

- Verify backend database migration was run
- Check that `GRACE_PERIOD_DAYS` is set in `.env`
- Ensure subscription expired or payment failed (not cancelled by user)

### "Trial not showing up"

- Verify trial is configured in Google Play Console
- Check that user hasn't used trial before
- Ensure subscription product (not in-app product) is used

---

## Next Steps

1. ✅ Configure all three products in Google Play Console
2. ✅ Set up Google Cloud service account
3. ✅ Enable Google Play Developer API
4. ✅ Download service account JSON key
5. ✅ Link service account to Play Console
6. ✅ Configure backend with service account
7. ✅ Run database migration
8. ✅ Test with test accounts
9. ✅ (Optional) Set up Real-time Developer Notifications
10. ✅ Publish app or promote to testing track

---

## Support

For issues specific to:
- **Google Play Console**: [Google Play Console Help](https://support.google.com/googleplay/android-developer/)
- **Pinpoint App**: Check the main README.md
- **Backend Integration**: Check `payment_service.py` implementation

---

**Last Updated**: 2025-11-11
**Version**: 1.0.0
