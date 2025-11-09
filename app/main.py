"""
Pinpoint Backend API - Main Application
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import api_router
from app.database import init_db

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Privacy-first note-taking backend with end-to-end encryption",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Pinpoint API...")

    # Check for required configuration files
    print("🔍 Checking required configuration files...")

    required_files = {
        ".env": ".env file (contains database and API configuration)",
        settings.FCM_CREDENTIALS_PATH: "Firebase Admin SDK credentials (required for authentication)"
    }

    missing_files = []
    for file_path, description in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append(f"  ❌ {file_path} - {description}")
            print(f"❌ Missing: {file_path}")
        else:
            print(f"✅ Found: {file_path}")

    if missing_files:
        error_msg = "\n\n" + "="*70 + "\n"
        error_msg += "❌ CONFIGURATION ERROR: Required files are missing!\n"
        error_msg += "="*70 + "\n\n"
        error_msg += "Missing files:\n"
        error_msg += "\n".join(missing_files)
        error_msg += "\n\n"
        error_msg += "Please ensure all required files are present before starting the server.\n"
        error_msg += "See CREDENTIALS_SETUP_GUIDE.md for instructions.\n"
        error_msg += "="*70 + "\n"

        print(error_msg, file=sys.stderr)
        sys.exit(1)

    print(f"📊 Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    # Initialize database tables
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Shutting down Pinpoint API...")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pinpoint-api",
        "version": "1.0.0"
    }


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Pinpoint API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
