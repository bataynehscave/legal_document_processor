import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register uniform, production-ready exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception on %s %s: [%s] %s",
            request.method,
            request.url.path,
            exc.error_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        cleaned_errors = []
        for error in exc.errors():
            cleaned_errors.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            })

        return JSONResponse(
            status_code=422,
            content={
                "detail": "Invalid request payload format or missing required fields.",
                "error_code": "REQUEST_VALIDATION_ERROR",
                "details": cleaned_errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.warning("HTTPException %s on %s %s", exc.status_code, request.method, request.url.path)
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": "RATE_LIMIT_EXCEEDED" if exc.status_code == 429 else "HTTP_EXCEPTION",
            },
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )
