"""ASGI logging middleware used during development.

This middleware emits log entries for every incoming request and optionally
publishes CloudWatch metrics when boto3 is available.  It remains lightweight
so it can be shared across branches without merge conflicts.
"""
from __future__ import annotations

import json
import logging
import time
from typing import MutableMapping, Optional, cast

from starlette.types import ASGIApp, Receive, Scope, Send

try:  # pragma: no cover - exercised indirectly via tests
    import boto3  # type: ignore
except Exception:  # pragma: no cover - boto3 is optional
    boto3 = None  # type: ignore


LOG_LEVEL: int = 1  # 0 = silent, 1 = info, 2 = debug
CLOUDWATCH_NAMESPACE = "ECE461/API"
CLOUDWATCH_AVAILABLE = boto3 is not None

logger = logging.getLogger("backend.middleware.logging")


class LoggingMiddleware:
    """Simple request/response logger for ASGI apps."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.cloudwatch = None
        if CLOUDWATCH_AVAILABLE and boto3 is not None:  # pragma: no branch - simple guard
            try:
                self.cloudwatch = boto3.client("cloudwatch")
            except Exception:  # pragma: no cover - exercised in tests
                logger.debug("CloudWatch client initialisation failed", exc_info=True)
                self.cloudwatch = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        start = time.perf_counter()
        status_holder: dict[str, Optional[int]] = {"status": None}

        async def send_wrapper(message: MutableMapping[str, object]) -> None:
            if message.get("type") == "http.response.start":
                status_holder["status"] = cast(Optional[int], message.get("status"))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            status = status_holder["status"] or 0
            self._log_success(method, path, status, time.perf_counter() - start)
            self._send_metrics(method, path, status, success=True)
        except Exception as exc:  # pragma: no cover - runtime guard
            self._log_error(method, path, exc)
            self._send_metrics(method, path, 500, success=False)
            raise

    async def dispatch(self, request, call_next):
        """Compatibility shim for tests using a Request object."""

        method = getattr(request, "method", "")
        path = getattr(getattr(request, "url", None), "path", "")
        client = getattr(getattr(request, "client", None), "host", "unknown")
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 0)
            self._log_success(method, path, status, time.perf_counter() - start, client)
            self._send_metrics(method, path, status, success=True)
            return response
        except Exception as exc:
            self._log_error(method, path, exc, client)
            self._send_metrics(method, path, 500, success=False)
            raise

    def _log_success(self, method: str, path: str, status: int, duration: float, client: str | None = None) -> None:
        duration_ms = duration * 1000
        if LOG_LEVEL >= 1:
            message = f"Request: {method} {path} | Status: {status} | Duration: {duration_ms:.2f} ms"
            logger.info(message)
        if LOG_LEVEL >= 2:
            debug_payload = {
                "type": "request",
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": duration_ms,
                "client": client,
            }
            logger.debug(json.dumps(debug_payload))

    def _log_error(self, method: str, path: str, exc: Exception, client: str | None = None) -> None:
        if LOG_LEVEL >= 1:
            logger.info(f"Error: {method} {path} -> {exc}")
        if LOG_LEVEL >= 2:
            debug_payload = {
                "type": "error",
                "method": method,
                "path": path,
                "error": str(exc),
                "client": client,
            }
            logger.debug(json.dumps(debug_payload))

    def _send_metrics(self, method: str, path: str, status: int, *, success: bool) -> None:
        if not self.cloudwatch:
            return
        try:
            self.cloudwatch.put_metric_data(  # type: ignore[call-arg]
                Namespace=CLOUDWATCH_NAMESPACE,
                MetricData=[
                    {
                        "MetricName": "http_request",
                        "Dimensions": [
                            {"Name": "status_code", "Value": str(status)},
                            {"Name": "outcome", "Value": "success" if success else "error"},
                        ],
                        "Value": 1,
                        "Unit": "Count",
                    }
                ],
            )
        except Exception:  # pragma: no cover - exercised via tests
            logger.debug("CloudWatch put_metric_data failed", exc_info=True)
            self.cloudwatch = None


def setup_logging(app: ASGIApp) -> ASGIApp:
    """Convenience helper mirroring the previous middleware interface."""

    return LoggingMiddleware(app)
