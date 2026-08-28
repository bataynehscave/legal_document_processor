from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import setup_exception_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.middleware import SecurityAndTracingMiddleware
from app.services.job_queue import job_queue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown event handling."""
    # Startup
    await init_db()
    await job_queue.start()
    yield
    # Shutdown
    await job_queue.stop()


def create_application() -> FastAPI:
    """FastAPI application factory with production configurations."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Production-ready API for extracting, validating, and querying legal lease agreement metadata "
            "with native LLM orchestration, async background queueing, rate limiting, and deterministic business rules."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware Stack (Security headers, payload size guard, request tracing)
    app.add_middleware(SecurityAndTracingMiddleware)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time-Ms",
            "Retry-After",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    # Register Uniform Global Exception Handlers
    setup_exception_handlers(app)

    # Include API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check probe endpoint."""
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "provider": settings.LLM_PROVIDER,
        }

    return app


app = create_application()
