# Service Account Credentials Setup Guide

This guide explains how to obtain the real service account JSON files needed for Firebase and Google Play integration.

## 📋 Overview

You need two service account JSON files:
1. **Firebase Admin SDK** - For push notifications
2. **Google Play Service Account** - For subscription verification

---

## 🔥 Firebase Admin SDK Setup

### Step 1: Go to Firebase Console
1. Visit https://console.firebase.google.com/
2. Select your project (or create a new one)

### Step 2: Navigate to Service Accounts
1. Click the **gear icon** ⚙️ (Project Settings) in the top left
2. Go to the **Service accounts** tab
3. You should see: "Firebase Admin SDK"

### Step 3: Generate New Private Key
1. Click **"Generate new private key"** button
2. A dialog will appear warning that the key is sensitive
3. Click **"Generate key"**
4. A JSON file will be downloaded to your computer

### Step 4: Use the Downloaded File
1. Rename the downloaded file to `firebase-admin-sdk.json`
2. Move it to: `G:\MyProjects\pinpoint_backend\firebase-admin-sdk.json`
3. **IMPORTANT:** Add to `.gitignore` to avoid committing to Git!

**Example file structure:**
```json
{
  "type": "service_account",
  "project_id": "pinpoint-app-12345",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xyz@pinpoint-app-12345.iam.gserviceaccount.com",
  ...
}
```

---

## 🎮 Google Play Service Account Setup

### Step 1: Access Google Play Console
1. Visit https://play.google.com/console/
2. Select your app (or create one)
3. Go to **Setup** → **API access**

### Step 2: Link Google Cloud Project
If not already linked:
1. Click **"Link to a Google Cloud project"** or **"Create new Google Cloud project"**
2. Follow the prompts to link/create

### Step 3: Create Service Account

**Option A: Create from Google Play Console**
1. In API access, scroll to "Service accounts"
2. Click **"Create new service account"**
3. This will open Google Cloud Console in a new tab

**Option B: Create from Google Cloud Console directly**
1. Go to https://console.cloud.google.com/
2. Select your project
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **"+ CREATE SERVICE ACCOUNT"**

### Step 4: Configure Service Account
1. **Service account name:** `pinpoint-google-play` (or any name)
2. **Service account description:** "Service account for Google Play purchase verification"
3. Click **"CREATE AND CONTINUE"**

### Step 5: Grant Permissions (IMPORTANT!)
Grant these roles:
- **No roles needed** at Cloud project level (click "CONTINUE" to skip)

### Step 6: Create Key
1. After creating the service account, click on it
2. Go to **"KEYS"** tab
3. Click **"ADD KEY"** → **"Create new key"**
4. Select **"JSON"** format
5. Click **"CREATE"**
6. The JSON file will be downloaded

### Step 7: Grant Access in Google Play Console
**CRITICAL STEP - Don't skip!**

1. Go back to Google Play Console → **Setup** → **API access**
2. Under "Service accounts", find your newly created service account
3. Click **"Manage Play Console permissions"** or **"Grant access"**
4. In the permissions dialog, grant:
   - **Financials → View financial data** ✅
   - **App information → View app information** ✅
   - **Orders and subscriptions → Manage orders and subscriptions** ✅
5. Click **"Invite user"** or **"Apply"**

### Step 8: Use the Downloaded File
1. Rename the downloaded file to `google-play-service-account.json`
2. Move it to: `G:\MyProjects\pinpoint_backend\google-play-service-account.json`
3. **IMPORTANT:** Add to `.gitignore`!

**Example file structure:**
```json
{
  "type": "service_account",
  "project_id": "api-1234567890",
  "private_key_id": "def456...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "pinpoint-play@api-1234567890.iam.gserviceaccount.com",
  ...
}
```

---

## 🔒 Security Best Practices

### .gitignore Configuration
Add these lines to your `.gitignore`:
```
# Service account credentials (NEVER COMMIT!)
firebase-admin-sdk.json
google-play-service-account.json
*.pem
*.key
```

### Environment Variables
Update your `.env` file:
```bash
# Firebase
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-admin-sdk.json

# Google Play
GOOGLE_PLAY_SERVICE_ACCOUNT_PATH=/path/to/google-play-service-account.json
GOOGLE_PLAY_PACKAGE_NAME=com.example.pinpoint
```

### File Permissions
Set restrictive permissions (Linux/Mac):
```bash
chmod 600 firebase-admin-sdk.json
chmod 600 google-play-service-account.json
```

---

## ✅ Testing Setup

### Test Firebase Connection
```python
# test_firebase.py
import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("firebase-admin-sdk.json")
firebase_admin.initialize_app(cred)
print("✅ Firebase initialized successfully!")
```

### Test Google Play Connection
```python
# test_google_play.py
from google.oauth2 import service_account
from googleapiclient.discovery import build

credentials = service_account.Credentials.from_service_account_file(
    'google-play-service-account.json',
    scopes=['https://www.googleapis.com/auth/androidpublisher']
)

service = build('androidpublisher', 'v3', credentials=credentials)
print("✅ Google Play API initialized successfully!")
```

---

## 🚨 Troubleshooting

### Firebase Admin SDK Issues

**Error: "The default Firebase app does not exist"**
- Ensure `firebase-admin-sdk.json` exists
- Check the file path in your code
- Verify JSON is valid (not corrupted)

**Error: "Permission denied"**
- Firebase project might not have proper permissions
- Regenerate the service account key
- Ensure the service account has "Firebase Admin" role

### Google Play API Issues

**Error: "The caller does not have permission"**
- Service account not granted access in Play Console
- Go to Play Console → API access → Grant permissions
- Must grant "Financial data" and "Orders" permissions

**Error: "Invalid JSON"**
- Check JSON file is not corrupted
- Download the key again from Cloud Console
- Ensure no extra characters or whitespace

**Error: "Token has been expired or revoked"**
- Service account key might be deleted/revoked
- Create a new key in Cloud Console
- Update your JSON file

---

## 📚 Additional Resources

### Firebase Documentation
- [Firebase Admin SDK Setup](https://firebase.google.com/docs/admin/setup)
- [Service Account Credentials](https://cloud.google.com/iam/docs/service-accounts)

### Google Play Documentation
- [Google Play Developer API](https://developers.google.com/android-publisher)
- [Using the API](https://developers.google.com/android-publisher/getting_started)
- [Subscription Verification](https://developer.android.com/google/play/billing/security)

### Google Cloud Console
- [Service Accounts Management](https://console.cloud.google.com/iam-admin/serviceaccounts)
- [API Library](https://console.cloud.google.com/apis/library)

---

## 📝 Quick Checklist

Before running your backend:

- [ ] Firebase Admin SDK JSON downloaded
- [ ] Firebase JSON placed in backend directory
- [ ] Firebase JSON added to `.gitignore`
- [ ] Google Play service account created
- [ ] Google Play permissions granted in Play Console
- [ ] Google Play JSON downloaded
- [ ] Google Play JSON placed in backend directory
- [ ] Google Play JSON added to `.gitignore`
- [ ] `.env` file updated with paths
- [ ] Package name matches Google Play Console
- [ ] Tested both connections with test scripts

---

## 🎯 Final Notes

**NEVER commit these files to Git!**
- They contain private keys
- Anyone with these files can impersonate your app
- Keep them secure and backed up separately

**For Production:**
- Use environment variables or secret management
- Consider using Google Secret Manager
- Rotate keys regularly (every 90 days recommended)
- Monitor service account usage in Cloud Console

**For Development:**
- The backend will work in "mock mode" without these files
- You'll see warnings but purchases will be simulated
- Real verification requires real credentials

---

Need help? Check the troubleshooting section or consult the official documentation linked above.
