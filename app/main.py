"""
Pinpoint Backend API - Main Application
"""
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
    print(f"📊 Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    # Initialize database tables
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")


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
