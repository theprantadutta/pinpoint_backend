# UTC Timezone Handling

This document confirms that the entire reminder notification system uses UTC time consistently across frontend, backend, and Celery to prevent timezone-related issues when servers are in different timezones.

## Backend (Python/FastAPI)

### ✅ Celery Configuration
**File:** `celery_app.py`
```python
timezone="UTC"
enable_utc=True
```
- All Celery tasks execute in UTC
- All scheduled times are interpreted as UTC
- Beat scheduler runs in UTC

### ✅ Database Model
**File:** `app/models/reminder.py`
```python
reminder_time = Column(DateTime, nullable=False, index=True)
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
triggered_at = Column(DateTime, nullable=True)
```
- All datetime columns use `datetime.utcnow()`
- Times stored in database are UTC
- No timezone-aware datetimes needed (PostgreSQL stores as UTC)

### ✅ Service Layer
**File:** `app/services/reminder_service.py`
```python
now = datetime.utcnow()  # Line 279, 309
```
- All time comparisons use UTC
- Task scheduling uses UTC

### ✅ Celery Tasks
**File:** `app/tasks/reminder_tasks.py`
```python
now = datetime.utcnow()  # Line 154
```
- Missed reminder checks use UTC
- All time comparisons in UTC

### ✅ API Schemas
**File:** `app/schemas/reminder.py`
```python
reminder_time: datetime = Field(..., description="When to send the reminder (UTC)")
reminder_time: Optional[datetime] = Field(None, description="New reminder time (UTC)")
```
- Documentation explicitly states UTC
- Pydantic automatically handles ISO 8601 string parsing

## Frontend (Flutter/Dart)

### ✅ Data Transfer Object
**File:** `lib/models/reminder_dto.dart`

**Sending to API (always converts to UTC):**
```dart
// Create request
'reminder_time': reminderTime.toUtc().toIso8601String()  // Line 31

// Update request
'reminder_time': reminderTime.toUtc().toIso8601String()  // Line 40

// Sync request
'reminder_time': reminderTime.toUtc().toIso8601String()  // Line 50
```

**Receiving from API (converts to local for display):**
```dart
// Response parsing
reminderTime: DateTime.parse(json['reminder_time']).toLocal()  // Line 61
triggeredAt: DateTime.parse(json['triggered_at']).toLocal()    // Line 64
createdAt: DateTime.parse(json['created_at']).toLocal()        // Line 67
updatedAt: DateTime.parse(json['updated_at']).toLocal()        // Line 70
```

### ✅ API Service
**File:** `lib/services/api_service.dart`
```dart
'reminder_time': reminderTime.toUtc().toIso8601String()
```
- All API calls convert DateTime to UTC ISO 8601 strings

### ✅ Local Storage
**File:** `lib/services/reminder_note_service.dart`
- Local database stores times in local timezone (for display)
- When syncing to backend, automatically converted to UTC via DTO

## Data Flow

### Creating a Reminder

1. **User selects time** → Local timezone (e.g., 2PM PST)
2. **Saved to local DB** → Local timezone (2PM PST)
3. **DTO conversion** → `.toUtc()` → UTC (10PM UTC)
4. **API request** → ISO 8601 UTC string (`"2025-11-16T22:00:00Z"`)
5. **Backend receives** → Pydantic parses as UTC
6. **Stored in PostgreSQL** → UTC (10PM UTC)
7. **Celery schedules** → UTC (10PM UTC)

### Triggering a Reminder

1. **Celery Beat checks** → Current time in UTC
2. **Compares with reminder_time** → Both in UTC
3. **Task executes** → At exact UTC time
4. **FCM notification sent** → User's device shows in local time

### Syncing Existing Reminders

1. **Local DB has reminder** → Local time (2PM PST)
2. **ReminderSyncService reads** → Local time
3. **fromLocal() creates DTO** → Stores local time
4. **toJsonSync() converts** → `.toUtc()` → UTC (10PM UTC)
5. **Backend receives** → UTC time
6. **Schedules correctly** → UTC (10PM UTC)

## Server Timezone Independence

✅ **Backend can be deployed anywhere:**
- Server in US (PST): Uses UTC internally
- Server in Europe (CET): Uses UTC internally
- Server in Asia (JST): Uses UTC internally

✅ **Celery workers can be anywhere:**
- Configured with `timezone="UTC"`
- All scheduling in UTC
- Independent of server's system timezone

✅ **Database can be anywhere:**
- PostgreSQL stores timestamps without timezone
- Application always provides UTC
- No implicit timezone conversions

## Testing Timezone Correctness

### Test 1: Create reminder in different timezone
```bash
# User in PST creates reminder for 2PM local
# Backend should store as 10PM UTC
# Celery should schedule for 10PM UTC
```

### Test 2: Server moves to different timezone
```bash
# Move server from PST to UTC
# All existing reminders should fire at correct time
# Because everything uses UTC
```

### Test 3: User travels to different timezone
```bash
# User creates reminder in PST, travels to EST
# Reminder fires at correct local time (10AM EST = 2PM PST originally)
# Because client converts UTC to local for display
```

## Common Pitfalls Avoided

❌ **Don't do:** `datetime.now()` - uses server's local timezone
✅ **Do:** `datetime.utcnow()` - always UTC

❌ **Don't do:** Store local time in database
✅ **Do:** Convert to UTC before storing

❌ **Don't do:** Compare local time with UTC time
✅ **Do:** Always compare in same timezone (UTC)

❌ **Don't do:** Hardcode timezone in Celery
✅ **Do:** Use `timezone="UTC"` and `enable_utc=True`

## Summary

🌍 **Everywhere in the system:**
- Backend: UTC (`datetime.utcnow()`)
- Database: UTC timestamps
- Celery: UTC scheduling (`timezone="UTC"`)
- API: UTC ISO 8601 strings
- Frontend: Converts to UTC when sending, local when displaying

This ensures reminders fire at the correct time regardless of:
- Server location
- User location
- Database location
- Celery worker location
