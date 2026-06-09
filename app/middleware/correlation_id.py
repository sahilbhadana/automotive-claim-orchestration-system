from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Propagate or mint a Correlation-ID for every request.

    - If the client sends ``X-Correlation-ID``, that value is echoed back.
    - Otherwise a new UUID4 is generated and attached to both the request
      state and the response headers.
    - ``X-Request-ID`` is always generated fresh per request so callers can
      distinguish retries within the same logical operation.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        )
        request_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
