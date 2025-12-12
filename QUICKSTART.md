# Pinpoint Backend - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.11+
- PostgreSQL database (already configured)
- Git

### Step 1: Clone and Navigate
```bash
cd G:\MyProjects\pinpoint_backend
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Database
```bash
# Create initial migration
alembic revision --autogenerate -m "Initial tables"

# Apply migrations
alembic upgrade head
```

### Step 5: Run the Server
```bash
python run.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8645
```

### Step 6: Access API Docs
Open in your browser:
- **Swagger UI**: http://localhost:8645/docs
- **ReDoc**: http://localhost:8645/redoc
- **Health Check**: http://localhost:8645/health

## 🧪 Test the API

### Register a User
```bash
curl -X POST "http://localhost:8645/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8645/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

This returns a JWT token. Use it in subsequent requests:

### Get User Info
```bash
curl -X GET "http://localhost:8645/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Sync Notes (Encrypted)
```bash
curl -X POST "http://localhost:8645/api/v1/notes/sync" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": [
      {
        "client_note_id": 1,
        "encrypted_data": "base64_encrypted_data_here",
        "metadata": {
          "type": "text",
          "updated_at": "2024-11-08T10:00:00Z"
        }
      }
    ],
    "device_id": "test_device_123"
  }'
```

## 🐳 Docker Deployment

### Using Docker Compose
```bash
docker-compose up -d
```

This starts:
- Backend API on port 8645
- Redis on port 6379 (for caching)

### Access the API
```
http://localhost:8645/docs
```

## 📦 Project Structure

```
pinpoint_backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Security & dependencies
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
├── alembic/             # Database migrations
├── .env                 # Environment variables
├── requirements.txt     # Dependencies
└── docker-compose.yml   # Docker setup
```

## 🔧 Development Tips

### Run with Hot Reload
```bash
uvicorn app.main:app --reload
```

### Create Database Migration
```bash
alembic revision --autogenerate -m "Add new field"
alembic upgrade head
```

### View Database
Use your favorite PostgreSQL client with these credentials:
- Host: pranta.vps.webdock.cloud
- Port: 5432
- Database: pinpoint
- User: postgres

## 🔐 Security Notes

⚠️ **IMPORTANT**: The `.env` file contains sensitive credentials and is gitignored.

For production:
1. Change JWT_SECRET_KEY to a strong random value
2. Enable SSL for database connection
3. Configure proper CORS origins
4. Use HTTPS only
5. Set up proper firewall rules

## 📱 Integrate with Flutter App

In your Flutter app, update the API base URL:

```dart
// lib/services/api_service.dart
static const String baseUrl = 'http://localhost:8645'; // Development
// static const String baseUrl = 'https://api.pinpoint.app'; // Production
```

## 🆘 Troubleshooting

### Database Connection Error
- Check if database credentials in `.env` are correct
- Verify database is accessible from your network
- Check firewall settings

### Module Not Found Error
```bash
pip install -r requirements.txt
```

### Alembic Migration Error
```bash
# Reset and recreate migrations
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

## 📚 Next Steps

1. ✅ Set up Firebase credentials for push notifications
2. ✅ Add Google Play service account for payment verification
3. ✅ Configure production environment
4. ✅ Set up SSL/HTTPS
5. ✅ Deploy to production server

---

**Need help?** Check the main README.md or API documentation at `/docs`
