"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.routers import auth, openai_proxy, admin

# Configure logging
logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Starting {settings.APP_NAME}")

    # Initialize database tables
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="OpenAI-compatible API gateway with API key management, backed by LocalAI",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else "Something went wrong"}
    )


# Health check (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME}


# Root
@app.get("/")
async def root():
    """API info."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "OpenAI-compatible API gateway with LocalAI backend",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": "/auth",
            "openai_api": "/v1",
            "admin": "/admin",
        }
    }


# Include routers
app.include_router(auth.router)
app.include_router(openai_proxy.router)
app.include_router(admin.router)
