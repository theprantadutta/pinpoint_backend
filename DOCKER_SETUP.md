# Docker Setup for Backend with Celery

This setup includes the FastAPI backend, Celery worker, and Celery beat scheduler for reminder notifications.

## Prerequisites

- Redis running on host machine at `localhost:6379`

## Services

The docker-compose.yml defines 3 services:

1. **backend** - FastAPI application (port 84 → 8000)
2. **celery-worker** - Processes reminder notification tasks
3. **celery-beat** - Schedules periodic tasks (checks for missed reminders every 5 minutes)

All services connect to your existing Redis instance via `host.docker.internal:6379`.

## Quick Start

### 1. Start all services

```bash
cd pinpoint_backend
docker-compose up -d
```

This will:
- Build the Docker image if needed
- Start the FastAPI backend (with auto-reload)
- Start Celery worker (with 2 concurrent workers)
- Start Celery beat scheduler

**Note:** Make sure your Redis is running on localhost:6379 before starting!

### 2. Run database migrations

The backend service automatically runs `alembic upgrade head` on startup. But if you need to run it manually:

```bash
docker-compose exec backend alembic upgrade head
```

### 3. View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

### 4. Stop all services

```bash
docker-compose down
```

### 5. Rebuild after code changes

If you change dependencies in requirements.txt:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## How Reminders Work

1. User creates reminder in Flutter app
2. Flutter calls backend API (`POST /api/v1/reminders`)
3. Backend creates database record and schedules Celery task
4. Celery worker executes task at scheduled time
5. Task sends FCM notification to all user devices
6. Celery beat runs every 5 minutes to catch any missed reminders

## Monitoring

### Check Celery worker status

```bash
docker-compose exec celery-worker celery -A celery_app inspect active
```

### Check scheduled tasks

```bash
docker-compose exec celery-worker celery -A celery_app inspect scheduled
```

### Check Redis connection from containers

```bash
# Test from backend container
docker-compose exec backend python -c "import redis; r = redis.from_url('redis://host.docker.internal:6379'); print('PONG' if r.ping() else 'FAILED')"

# Or check on your host directly
redis-cli ping
# Should return: PONG
```

## Troubleshooting

### Celery worker not picking up tasks

First, make sure Redis is running on your host:
```bash
redis-cli ping
```

Check Redis connection from Celery worker:
```bash
docker-compose exec celery-worker python -c "import redis; r = redis.from_url('redis://host.docker.internal:6379'); print('Connected!' if r.ping() else 'Failed')"
```

### View Celery worker concurrency

```bash
docker-compose exec celery-worker celery -A celery_app inspect stats
```

### Restart specific service

```bash
docker-compose restart celery-worker
docker-compose restart celery-beat
docker-compose restart backend
```

## Development

The following directories are mounted for hot-reload:
- `./app` → `/app/app` (backend code)
- `./alembic` → `/app/alembic` (migrations)
- `./celery_app.py` → `/app/celery_app.py` (Celery config)

Changes to these files will automatically reload the services.

## Production Considerations

For production:
1. Remove `--reload` from backend command
2. Increase Celery worker concurrency based on load
3. Use managed Redis service (like AWS ElastiCache, Redis Cloud, etc.)
4. Update `REDIS_URL` in .env to point to production Redis
5. Add monitoring with Flower or Prometheus
6. Configure proper logging with centralized logging solution
7. Use proper secret management (not .env files)
