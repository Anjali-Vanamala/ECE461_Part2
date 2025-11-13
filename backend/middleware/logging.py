"""ASGI logging middleware used during development.

This middleware emits a concise log entry for every incoming request and its
corresponding response status.  It is intentionally lightweight so it can be
shared across branches without merge conflicts.
"""
from __future__ import annotations

import logging
import time

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("backend.middleware.logging")


class LoggingMiddleware:
    """Simple request/response logger for ASGI apps."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        start = time.perf_counter()
        status_holder: dict[str, int | None] = {"status": None}

        async def send_wrapper(message: MutableMapping[str, object]) -> None:
            if message.get("type") == "http.response.start":
                status_holder["status"] = message.get("status")
            await send(message)

        await self.app(scope, receive, send_wrapper)
        elapsed_ms = (time.perf_counter() - start) * 1000
        status = status_holder["status"] or 0
        logger.info("%s %s -> %s (%.2f ms)", method, path, status, elapsed_ms)


def setup_logging(app: ASGIApp) -> ASGIApp:
    """Convenience helper mirroring the previous middleware interface."""

    return LoggingMiddleware(app)
