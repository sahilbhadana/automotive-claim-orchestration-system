from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("app.access")

_SKIP_PATHS = {"/api/v1/metrics", "/api/v1/health", "/api/v1/ready"}


class RequestTracerMiddleware(BaseHTTPMiddleware):
    """Structured access log with request timing and correlation IDs.

    Emits one log line per request containing:
    - HTTP method and path
    - Response status code
    - Duration in milliseconds
    - Correlation-ID and Request-ID from request state (set by
      :class:`~app.middleware.correlation_id.CorrelationIDMiddleware`)
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            correlation_id = getattr(request.state, "correlation_id", "-")
            request_id = getattr(request.state, "request_id", "-")

            logger.info(
                "HTTP request",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "client_ip": (
                        request.client.host if request.client else "unknown"
                    ),
                },
            )

            try:
                from app.core.metrics import http_request_duration_seconds
                from app.core.metrics import http_requests_total

                label_path = request.url.path.split("?")[0]
                http_request_duration_seconds.labels(
                    method=request.method,
                    path=label_path,
                    status_code=str(status_code),
                ).observe(duration_ms / 1000)
                http_requests_total.labels(
                    method=request.method,
                    path=label_path,
                    status_code=str(status_code),
                ).inc()
            except Exception:
                pass
