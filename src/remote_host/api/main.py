"""
Main FastAPI application with security hardening.

Provides:
- REST API for security tool orchestration
- Authentication & authorization
- Rate limiting
- Security headers
- CORS configuration
- Logging & monitoring
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from ..config import get_settings
from ..database import close_db, create_tables, init_db
from .routers import health, router_comm, scans

# Rate limiting state (simple in-memory implementation)
# For production, use Redis-based rate limiting
_rate_limit_store: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    settings = get_settings()

    # Startup
    logger.info("Starting Beryl AX Pineapple server...")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Create tables in development (use Alembic in production)
    if settings.is_development:
        await create_tables()
        logger.info("Database tables created")

    # Log configuration
    logger.info(f"Router: {settings.router_host}:{settings.router_port}")
    logger.info(f"MCP enabled: {settings.mcp_enabled}")
    logger.info(f"AI analysis enabled: {settings.ai_analysis_enabled}")

    yield

    # Shutdown
    logger.info("Shutting down Beryl AX Pineapple server...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title="Beryl AX Pineapple",
    description="AI-driven security automation for GL.iNet Beryl AX (MT-3000)",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)


# =============================================================================
# Security Middleware
# =============================================================================


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Remove server header
    response.headers.pop("Server", None)

    return response


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """
    Simple rate limiting middleware.

    For production, use Redis-based rate limiting like slowapi or fastapi-limiter.
    """
    if not settings.rate_limit_enabled:
        return await call_next(request)

    # Get client identifier (IP address)
    client_ip = request.client.host if request.client else "unknown"

    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)

    current_time = time.time()

    # Get or create rate limit bucket for this client
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Remove old timestamps (older than 1 minute)
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if current_time - ts < 60
    ]

    # Check rate limit
    if len(_rate_limit_store[client_ip]) >= settings.rate_limit_per_minute:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Maximum {settings.rate_limit_per_minute} requests per minute",
            },
            headers={"Retry-After": "60"},
        )

    # Add current request
    _rate_limit_store[client_ip].append(current_time)

    return await call_next(request)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s"
    )

    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# =============================================================================
# CORS Configuration
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# =============================================================================
# Additional Middleware
# =============================================================================

# Gzip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host middleware (prevent host header attacks)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.host],
    )


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    logger.error(f"ValueError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid input", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred" if settings.is_production else str(exc),
        },
    )


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(router_comm.router, prefix="/api/router", tags=["router"])


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Beryl AX Pineapple API",
        "version": "0.1.0",
        "description": "AI-driven security automation for GL.iNet Beryl AX (MT-3000)",
        "docs": "/docs" if not settings.is_production else "disabled",
        "health": "/health",
    }


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Run the server using uvicorn."""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "remote_host.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
