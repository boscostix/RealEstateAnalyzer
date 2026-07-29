"""Application logging configuration and request context middleware."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("real_estate_analyzer")


def configure_logging(level: str = "INFO") -> None:
    """Configure standard application logging once."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a request id and basic timing information to each request."""

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.request_started_at = time.perf_counter()

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def add_middleware(app: FastAPI) -> None:
    """Register middleware used across the application."""

    app.middleware("http")(request_context_middleware)
