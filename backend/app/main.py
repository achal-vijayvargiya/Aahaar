"""
FastAPI main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings, BACKEND_CORS_ORIGINS
from app.database import init_db
from app.utils.logger import logger
from app.routers import auth, users, clients, appointments, health_profiles, dosha_quiz, gut_health_quiz, diet_plans


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting DrAssistent API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down DrAssistent API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Healthcare Assistant Management API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(clients.router, prefix=settings.API_V1_PREFIX)
app.include_router(appointments.router, prefix=settings.API_V1_PREFIX)
app.include_router(health_profiles.router, prefix=settings.API_V1_PREFIX)
app.include_router(dosha_quiz.router, prefix=settings.API_V1_PREFIX)
app.include_router(gut_health_quiz.router, prefix=settings.API_V1_PREFIX)
app.include_router(diet_plans.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to DrAssistent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

