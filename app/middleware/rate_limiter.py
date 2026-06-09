from __future__ import annotations

import time
from collections import defaultdict
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.types import ASGIApp


class InMemoryRateLimiter(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed on client IP.

    Defaults: 100 requests per 60-second window.
    Auth endpoints get a tighter window: 10 requests per 60 seconds.
    """

    _AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}

    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        auth_limit: int = 10,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            return True, 0

        bucket.append(now)
        remaining = limit - len(bucket)
        return False, remaining

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        key = self._get_client_key(request)
        limit = self.auth_limit if path in self._AUTH_PATHS else self.default_limit

        limited, remaining = self._is_rate_limited(f"{key}:{path}", limit)
        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": self.window_seconds,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = f"{self.window_seconds}s"
        return response
