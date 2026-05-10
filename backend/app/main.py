"""
FastAPI application entry point for EmailGuardian.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.routes import auth_router, emails_router, analytics_router
from app.services.scheduler import scheduler_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown events.
    """
    # Startup
    logger.info("Starting EmailGuardian...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start scheduler
    scheduler_service.start()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EmailGuardian...")
    
    # Stop scheduler
    scheduler_service.stop()
    
    # Close database connections
    await close_db()
    
    logger.info("EmailGuardian stopped")


# Create FastAPI app
app = FastAPI(
    title="EmailGuardian API",
    description="Intelligent Email Monitor & Summarizer - AI-powered email management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(emails_router)
app.include_router(analytics_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "name": "EmailGuardian API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.is_running,
        "scheduled_jobs": scheduler_service.get_job_status(),
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
