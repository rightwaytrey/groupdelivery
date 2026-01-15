from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.routers import addresses, drivers, optimization, auth, geocoding
import logging
import traceback

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup if needed


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Route optimization system for volunteer delivery services",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to prevent 502 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions to prevent 502 Bad Gateway errors."""
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url}:\n{error_trace}")

    # Don't override HTTP exceptions
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    # Return 500 for all other exceptions
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}: {str(exc)}",
            "type": type(exc).__name__
        }
    )


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include routers
app.include_router(auth.router)  # Auth endpoints (no protection needed)
app.include_router(addresses.router)
app.include_router(drivers.router)
app.include_router(optimization.router)
app.include_router(geocoding.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Docker healthcheck"""
    return {"status": "healthy"}


@app.get("/api/debug")
async def debug_info():
    """Debug endpoint to check backend status"""
    import sys
    import platform
    return {
        "status": "running",
        "app": settings.app_name,
        "version": settings.app_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "debug": True
    }
