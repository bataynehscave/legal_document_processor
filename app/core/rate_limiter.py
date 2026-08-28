import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status

from app.core.config import settings


class InMemorySlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter per client IP address."""

    def __init__(self, requests_per_minute: Optional[int] = None, window_seconds: int = 60) -> None:
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = self._get_client_ip(request)
        now = time.time()
        window_start = now - self.window_seconds

        async with self._lock:
            # Clean up old timestamps
            timestamps = [t for t in self._records[client_ip] if t > window_start]
            self._records[client_ip] = timestamps

            if len(timestamps) >= self.requests_per_minute:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(oldest_in_window + self.window_seconds - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: maximum {self.requests_per_minute} requests per minute. Try again in {retry_after}s.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                    },
                )

            self._records[client_ip].append(now)

    def reset(self) -> None:
        """Reset records (useful for testing)."""
        self._records.clear()


# Default singleton instance for general API rate limiting
rate_limiter = InMemorySlidingWindowRateLimiter()
