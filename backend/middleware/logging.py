"""ASGI logging middleware used during development.

This middleware emits log entries for every incoming request and optionally
publishes CloudWatch metrics when boto3 is available. It remains lightweight
so it can be shared across branches without merge conflicts.
"""
from __future__ import annotations

import json
import logging
import time
from typing import MutableMapping, Optional, cast

from starlette.types import ASGIApp, Receive, Scope, Send

try:
    import boto3  # type: ignore
except Exception:
    boto3 = None  # type: ignore

LOG_LEVEL: int = 1  # 0 = silent, 1 = info, 2 = debug
CLOUDWATCH_NAMESPACE = "ECE461/API"
CLOUDWATCH_AVAILABLE = boto3 is not None

logger = logging.getLogger("backend.middleware.logging")


import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("backend.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # ARRIVAL
        logger.info(f"[ARRIVED] {request.method} {request.url.path}")

        # Read body (make sure request.stream() stays readable)
        body = await request.body()
        if body:
            try:
                logger.info(f"[ARRIVED BODY] {body.decode('utf-8')}")
            except Exception:
                logger.info("[ARRIVED BODY] <unreadable>")

        # Timer
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        # AFTER REQUEST
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Status: {response.status_code} | Duration: {duration:.2f} ms"
        )

        return response


def setup_logging(app: ASGIApp) -> ASGIApp:
    return LoggingMiddleware(app)
