"""Request logging and error handling middleware."""

import logging
import time
import traceback
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions, return 500 with safe error message."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
