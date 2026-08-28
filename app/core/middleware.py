import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class SecurityAndTracingMiddleware(BaseHTTPMiddleware):
    """Production middleware handling request ID tracing, latency measurement, size guards, and security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Payload size guard (checks content-length header before reading body)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Payload too large. Maximum allowed size is {settings.MAX_PAYLOAD_BYTES} bytes.",
                    "error_code": "PAYLOAD_TOO_LARGE",
                    "details": {"max_bytes": settings.MAX_PAYLOAD_BYTES, "received_bytes": int(content_length)},
                },
            )

        # 2. Request ID tracing
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 3. Time execution
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # 4. Attach tracing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        # 5. Attach enterprise security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
