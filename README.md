# Pinpoint Backend API

Privacy-first note-taking backend built with FastAPI and PostgreSQL.

## Features

- 🔐 **End-to-End Encryption**: Notes are encrypted client-side before reaching the server
- 🔑 **Firebase Authentication**: Google Sign-In with Firebase token verification
- 💳 **Subscription Management**: Google Play purchase verification with grace periods
- 📊 **Usage Tracking**: Cloud-based limits for OCR, exports, and synced notes
- 🔔 **Push Notifications**: Firebase Cloud Messaging integration
- 🔄 **Real-time Sync**: Cross-device note synchronization
- 📈 **Auto-generated API Docs**: Swagger UI and ReDoc

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: Firebase Admin SDK + JWT
- **Push Notifications**: Firebase Cloud Messaging
- **Payment Verification**: Google Play Developer API
- **Server**: Uvicorn (ASGI)

## Project Structure

```
pinpoint_backend/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration from env
│   ├── database.py             # Database connection
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py             # User, UsageTracking
│   │   ├── note.py             # EncryptedNote
│   │   ├── subscription.py     # SubscriptionEvent
│   │   └── notification.py     # FCMToken
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── note.py
│   │   ├── auth.py
│   │   ├── subscription.py
│   │   └── usage.py            # Usage tracking schemas
│   │
│   ├── api/v1/                 # API routes
│   │   ├── auth.py             # Firebase auth endpoints
│   │   ├── notes.py            # Note sync endpoints
│   │   ├── subscription.py     # Google Play verification
│   │   ├── usage.py            # Usage tracking endpoints
│   │   └── notifications.py    # FCM token management
│   │
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── sync_service.py
│   │   ├── usage_service.py    # Usage limits & tracking
│   │   ├── payment_service.py
│   │   └── notification_service.py
│   │
│   └── core/                   # Core utilities
│       ├── security.py
│       └── dependencies.py
│
├── alembic/                    # Database migrations
│   └── versions/               # Migration files
├── run.py                      # Server startup script
├── .env                        # Environment variables (gitignored)
├── .env.example                # Example environment file
├── requirements.txt            # Python dependencies
└── README.md
```

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pinpoint_backend
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

**⚠️ IMPORTANT**: Never commit `.env` to Git! It contains sensitive credentials.

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start the Server

```bash
# Using run.py (recommended - uses configured port)
python run.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8645
```

The API will be available at:
- **API**: http://localhost:8645
- **Swagger Docs**: http://localhost:8645/docs
- **ReDoc**: http://localhost:8645/redoc

## API Documentation

### Authentication

Uses Firebase Authentication. The Flutter app obtains a Firebase ID token via Google Sign-In, which is then exchanged for a backend JWT.

#### Firebase Token Exchange
```http
POST /api/v1/auth/firebase
Content-Type: application/json

{
  "firebase_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "device_id": "unique_device_identifier"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_premium": false
  }
}
```

All subsequent requests use the `access_token` as a Bearer token.

### Notes Sync

#### Get All Notes
```http
GET /api/v1/notes/sync?since=1234567890
Authorization: Bearer <token>
```

#### Upload Encrypted Notes
```http
POST /api/v1/notes/sync
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": [
    {
      "client_note_id": 1,
      "encrypted_data": "base64_encrypted_blob",
      "metadata": {
        "type": "text",
        "updated_at": "2024-11-08T10:00:00Z"
      }
    }
  ],
  "device_id": "device_unique_id"
}
```

### Subscription

#### Verify Google Play Purchase
```http
POST /api/v1/subscription/verify
Authorization: Bearer <token>
Content-Type: application/json

{
  "purchase_token": "google_play_token",
  "product_id": "pinpoint_premium_monthly"
}
```

#### Check Subscription Status
```http
GET /api/v1/subscription/status
Authorization: Bearer <token>
```

### Usage Tracking

#### Get Usage Stats
```http
GET /api/v1/usage/stats
Authorization: Bearer <token>
```

Response:
```json
{
  "is_premium": false,
  "subscription_tier": "free",
  "synced_notes": { "current": 12, "limit": 50, "unlimited": false, "remaining": 38 },
  "ocr_scans": { "current": 5, "limit": 20, "unlimited": false, "remaining": 15 },
  "exports": { "current": 2, "limit": 10, "unlimited": false, "remaining": 8 },
  "last_updated": "2025-12-12T10:30:00Z"
}
```

#### Increment OCR Scans
```http
POST /api/v1/usage/ocr
Authorization: Bearer <token>
```

#### Increment Exports
```http
POST /api/v1/usage/export
Authorization: Bearer <token>
```

#### Reconcile Synced Notes Count
```http
POST /api/v1/usage/reconcile
Authorization: Bearer <token>
```

### Free Tier Limits

| Feature | Limit |
|---------|-------|
| Synced Notes | 50 total |
| OCR Scans | 20/month |
| Exports | 10/month |

> Monthly limits reset on the 1st of each month.

### Push Notifications

#### Register FCM Token
```http
POST /api/v1/notifications/register
Authorization: Bearer <token>
Content-Type: application/json

{
  "fcm_token": "firebase_cloud_messaging_token",
  "device_id": "device_unique_id",
  "platform": "android"
}
```

## Database Migrations

### Create a new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## Docker Deployment

### Build and run with Docker Compose

```bash
docker-compose up -d
```

### Access the API
```
http://localhost:8645
```

## Testing

Run tests with pytest:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` file
2. **JWT Secret**: Use a strong, random secret key in production
3. **HTTPS Only**: Always use HTTPS in production
4. **Database Credentials**: Rotate passwords regularly
5. **Firebase Credentials**: Keep service account JSON files secure
6. **Rate Limiting**: Implement rate limiting in production
7. **CORS**: Configure CORS properly for your Flutter app domains

## Production Deployment

### Using Railway (Recommended)

1. Push to GitHub
2. Connect Railway to your repository
3. Add environment variables
4. Deploy!

### Using DigitalOcean

1. Create a Droplet (Ubuntu 22.04)
2. Install Docker and Docker Compose
3. Clone repository
4. Configure `.env`
5. Run `docker-compose up -d`

## Environment Variables

See `.env.example` for all available configuration options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use this for your own projects!

## Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for privacy-focused note-taking**
