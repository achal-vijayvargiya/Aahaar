"""
FastAPI main application entry point.

This is the root entry point for the DrAssistent API application.
Uses platform routers following the NCP-aligned architecture.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings, BACKEND_CORS_ORIGINS
from app.database import init_db
from app.utils.logger import logger

# Platform routers (NCP-aligned architecture)
from app.platform.api.auth import router as platform_auth_router
from app.platform.api.clients import router as platform_clients_router
from app.platform.api.assessments import router as platform_assessments_router
from app.platform.api.plans import router as platform_plans_router
from app.platform.api.monitoring.monitoring import router as platform_monitoring_router
from app.platform.api.admin import router as platform_admin_router
from app.platform.api.quizzes import router as platform_quizzes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Handles startup and shutdown tasks:
    - Startup: Initialize database, log startup information
    - Shutdown: Log shutdown information
    """
    # Startup
    logger.info("Starting DrAssistent API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: 1.0.0")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Initialize database tables
    init_db()
    logger.info("Database initialized")
    
    # Log router registration
    logger.info("Registered platform routers at /api/v1/platform")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DrAssistent API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Healthcare Assistant Management API - Holistic Nutrition & Lifestyle Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PLATFORM ROUTERS
# ============================================================================
# These routers use the /api/v1/platform prefix
# They follow the NCP-aligned architecture
app.include_router(
    platform_auth_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Auth"]
)
app.include_router(
    platform_clients_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Clients"]
)
app.include_router(
    platform_quizzes_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Quizzes"]
)
app.include_router(
    platform_assessments_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Assessments"]
)
app.include_router(
    platform_plans_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Plans"]
)
app.include_router(
    platform_monitoring_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Monitoring"]
)
app.include_router(
    platform_admin_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Admin"]
)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint providing API information.
    
    Returns:
        dict: API metadata and available endpoints
    """
    return {
        "message": "Welcome to DrAssistent API",
        "version": "1.0.0",
        "description": "Healthcare Assistant Management API - Holistic Nutrition & Lifestyle Platform",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
        "platform_prefix": f"{settings.API_V1_PREFIX}/platform",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Health status and environment information
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

