# Pinpoint Backend API Documentation

## Base URL
```
Development: http://localhost:8000
Production: https://api.pinpoint.app
```

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## Endpoints

### Authentication

#### 1. Register User
**POST** `/api/v1/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**
- `400 Bad Request` - Email already registered

---

#### 2. Login
**POST** `/api/v1/auth/login`

Authenticate and get access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**
- `401 Unauthorized` - Invalid credentials

---

#### 3. Get Current User
**GET** `/api/v1/auth/me`

Get authenticated user information.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2024-11-08T10:00:00Z",
  "subscription_tier": "premium",
  "is_active": true,
  "is_premium": true
}
```

---

### Notes Synchronization

#### 4. Get Notes for Sync
**GET** `/api/v1/notes/sync?since=0&include_deleted=false`

Retrieve all encrypted notes for synchronization.

**Query Parameters:**
- `since` (int, optional): Unix timestamp for incremental sync (default: 0)
- `include_deleted` (bool, optional): Include soft-deleted notes (default: false)

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "client_note_id": 1,
    "encrypted_data": "base64_encoded_encrypted_blob",
    "metadata": {
      "type": "text",
      "updated_at": "2024-11-08T10:00:00Z",
      "has_audio": false,
      "is_archived": false
    },
    "version": 1,
    "created_at": "2024-11-08T09:00:00Z",
    "updated_at": "2024-11-08T10:00:00Z",
    "is_deleted": false
  }
]
```

---

#### 5. Upload/Sync Notes
**POST** `/api/v1/notes/sync`

Upload encrypted notes to the server.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "notes": [
    {
      "client_note_id": 1,
      "encrypted_data": "base64_encoded_encrypted_blob",
      "metadata": {
        "type": "text",
        "updated_at": "2024-11-08T10:00:00Z",
        "has_audio": false
      },
      "version": 1
    }
  ],
  "device_id": "device_unique_identifier"
}
```

**Response:** `200 OK`
```json
{
  "synced_count": 1,
  "updated_notes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "client_note_id": 1,
      "encrypted_data": "base64_encoded_encrypted_blob",
      "metadata": {...},
      "version": 1,
      "created_at": "2024-11-08T10:00:00Z",
      "updated_at": "2024-11-08T10:00:00Z",
      "is_deleted": false
    }
  ],
  "conflicts": [],
  "message": "Successfully synced 1 notes"
}
```

---

#### 6. Delete Notes
**DELETE** `/api/v1/notes/notes?hard_delete=false`

Delete notes (soft delete by default).

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Query Parameters:**
- `hard_delete` (bool, optional): Permanently delete vs soft delete (default: false)

**Request Body:**
```json
{
  "client_note_ids": [1, 2, 3]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "deleted_count": 3,
  "message": "Deleted 3 note(s)"
}
```

---

### Subscription

#### 7. Verify Google Play Purchase
**POST** `/api/v1/subscription/verify`

Verify a Google Play subscription purchase.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "purchase_token": "google_play_purchase_token",
  "product_id": "pinpoint_premium_monthly"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "tier": "premium",
  "expires_at": "2024-12-08T10:00:00Z",
  "message": "Subscription verified successfully"
}
```

**Errors:**
- `400 Bad Request` - Verification failed

---

#### 8. Get Subscription Status
**GET** `/api/v1/subscription/status`

Get current subscription status.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "is_premium": true,
  "tier": "premium",
  "expires_at": "2024-12-08T10:00:00Z",
  "product_id": "pinpoint_premium_monthly"
}
```

---

### Push Notifications

#### 9. Register FCM Token
**POST** `/api/v1/notifications/register`

Register Firebase Cloud Messaging token for push notifications.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "fcm_token": "firebase_cloud_messaging_token",
  "device_id": "device_unique_identifier",
  "platform": "android"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "FCM token registered successfully"
}
```

---

#### 10. Remove FCM Token
**DELETE** `/api/v1/notifications/token/{device_id}`

Remove FCM token for a device.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Path Parameters:**
- `device_id`: Device identifier

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Removed 1 token(s)"
}
```

---

#### 11. Send Push Notification
**POST** `/api/v1/notifications/send`

Send push notification to all user's devices.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Pinpoint",
  "body": "Your notes have been synced",
  "data": {
    "type": "sync_complete",
    "notes_count": "5"
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "sent_count": 2,
  "failed_count": 0,
  "message": "Sent 2 notifications, 0 failed"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200 OK` - Success
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions (e.g., premium required)
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Rate Limiting

**Note:** Rate limiting is not yet implemented but recommended for production:
- Authentication endpoints: 5 requests per minute
- Sync endpoints: 100 requests per minute
- Other endpoints: 60 requests per minute

---

## Security

### End-to-End Encryption Flow

1. **Client-side Encryption:**
   - Notes are encrypted using AES-256 before sending to server
   - User's encryption key is derived from their password (PBKDF2)
   - Key never leaves the device

2. **Server Storage:**
   - Server stores only encrypted blobs
   - Server cannot decrypt note content
   - Only encrypted metadata is stored for sync purposes

3. **Sync Process:**
   ```
   Device A                    Server                    Device B
      |                           |                           |
      | Encrypt note locally      |                           |
      | ----------------------->  |                           |
      |  (encrypted blob)         | Store encrypted blob     |
      |                           | <----------------------   |
      |                           |  Request sync             |
      |                           | ----------------------->  |
      |                           |  (encrypted blob)         |
      |                           |         Decrypt locally <-|
   ```

### Best Practices

1. **Always use HTTPS** in production
2. **Store JWT tokens securely** (Flutter Secure Storage)
3. **Never log sensitive data** (passwords, tokens)
4. **Rotate JWT secret** regularly in production
5. **Validate all inputs** client-side and server-side

---

## Webhooks (Future Feature)

Planned webhooks for real-time notifications:
- `subscription.created`
- `subscription.renewed`
- `subscription.cancelled`
- `note.synced`

---

## Interactive Documentation

Visit the auto-generated API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Both provide interactive API testing directly in the browser!
