"""Simple rate limiting middleware for API throttling."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Simple in-memory rate limiter
# Format: {client_ip: [timestamp1, timestamp2, ...]}
_request_history: dict[str, list[float]] = defaultdict(list)

# Rate limit: 100 requests per minute per IP
MAX_REQUESTS = 100
WINDOW_SECONDS = 60


class RateLimitMiddleware:
    """Simple rate limiting middleware."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the rate limiting middleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point for the middleware."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        # Get client IP
        client_ip = "unknown"
        if "client" in scope and scope["client"]:
            client_ip = scope["client"][0] if isinstance(scope["client"], tuple) else "unknown"

        # Check rate limit
        if not self._check_rate_limit(client_ip):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit."""
        now = time.time()
        history = _request_history[client_ip]

        # Remove old requests outside the window
        history[:] = [ts for ts in history if now - ts < WINDOW_SECONDS]

        # Check if limit exceeded
        if len(history) >= MAX_REQUESTS:
            return False

        # Add current request
        history.append(now)
        return True


def setup_rate_limit(app: ASGIApp) -> ASGIApp:
    """Wrap the ASGI app with rate limiting middleware."""
    return RateLimitMiddleware(app)
