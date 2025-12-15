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

# pylint: disable=invalid-name
try:
    import boto3  # type: ignore
except Exception:
    boto3 = None  # type: ignore

from backend.services.metrics_tracker import record_request

LOG_LEVEL: int = 1  # 0 = silent, 1 = info, 2 = debug
CLOUDWATCH_NAMESPACE = "ECE461/API"
CLOUDWATCH_AVAILABLE = boto3 is not None

logger = logging.getLogger("backend.middleware.logging")

# Sensitive field patterns to redact from logs
SENSITIVE_FIELDS = {
    "api_key", "apikey", "api-key",
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "bearer",
    "secret", "aws_secret_access_key", "aws_access_key_id",
    "authorization", "auth",
    "credit_card", "creditcard", "card_number",
}


def sanitize_json_string(text: str) -> str:
    """Sanitize JSON strings by redacting sensitive field values."""
    if not text or text == "<unreadable>":
        return text
    
    try:
        data = json.loads(text)
        sanitized = _sanitize_dict(data)
        return json.dumps(sanitized)
    except (json.JSONDecodeError, TypeError):
        # Not JSON, return as-is (non-JSON logs are less risky)
        return text


def _sanitize_dict(obj):
    """Recursively sanitize dictionary objects by redacting sensitive field values."""
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            key_lower = str(key).lower().replace("-", "_")
            
            # Check if this is a sensitive field
            if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            else:
                # Recursively sanitize nested structures
                sanitized[key] = _sanitize_dict(value)
        return sanitized
    elif isinstance(obj, list):
        return [_sanitize_dict(item) for item in obj]
    else:
        return obj


class LoggingMiddleware:
    """Simple request/response logger for ASGI apps."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the logging middleware."""
        self.app = app
        self.cloudwatch = None
        if CLOUDWATCH_AVAILABLE and boto3 is not None:
            try:
                self.cloudwatch = boto3.client("cloudwatch")
            except Exception:
                logger.debug("CloudWatch client initialization failed", exc_info=True)
                self.cloudwatch = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point for the middleware."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        start = time.perf_counter()
        status_holder: dict[str, Optional[int]] = {"status": None}

        # Extract client IP
        client_ip = None
        if "client" in scope and scope["client"]:
            client_ip = scope["client"][0] if isinstance(scope["client"], tuple) else None

        # Extract artifact type from path if applicable
        artifact_type = None
        if "/artifacts/" in path:
            parts = path.split("/artifacts/")
            if len(parts) > 1:
                artifact_type = parts[1].split("/")[0]

        # 🔥 LOG IMMEDIATELY WHEN REQUEST ARRIVES
        logger.info(f"[ARRIVED] {method} {path}")

        # Collect bodies as they stream
        body_store: list[bytes] = []
        response_body_store: list[bytes] = []

        async def receive_wrapper():
            """Wrap the receive callable to capture the request body."""
            message = await receive()

            if message.get("type") == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    body_store.append(chunk)

                if not message.get("more_body", False):
                    try:
                        raw_body = b"".join(body_store).decode("utf-8", errors="replace")
                        sanitized_body = sanitize_json_string(raw_body)
                    except Exception:
                        sanitized_body = "<unreadable>"
                    logger.info(f"[ARRIVED BODY] {sanitized_body}")

            return message

        async def send_wrapper(message: MutableMapping[str, object]) -> None:
            """Wrap the send callable to capture the response status and body."""
            msg_type = message.get("type")

            if msg_type == "http.response.start":
                status_holder["status"] = cast(Optional[int], message.get("status"))

            elif msg_type == "http.response.body":
                chunk = cast(bytes, message.get("body", b""))
                if chunk:
                    response_body_store.append(chunk)

                if not message.get("more_body", False):
                    try:
                        raw_response = b"".join(response_body_store).decode(
                            "utf-8", errors="replace"
                        )
                        sanitized_response = sanitize_json_string(raw_response)
                    except Exception:
                        sanitized_response = "<unreadable>"
                    logger.info(f"[RESPONSE BODY] {sanitized_response}")

            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)

            status = status_holder["status"] or 0

            # Record request for metrics (skip health endpoints to avoid recursion)
            if not path.startswith("/health"):
                record_request(method, path, status, client_ip, artifact_type)

            try:
                raw_body = b"".join(body_store).decode("utf-8", errors="replace")
                sanitized_body = sanitize_json_string(raw_body)
            except Exception:
                sanitized_body = "<unreadable>"
            logger.info(f"Request body: {sanitized_body}")

            self._log_success(method, path, status, time.perf_counter() - start)
            self._send_metrics(method, path, status, success=True)

        except Exception as exc:
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
        """Log a successful request."""
        duration_ms = duration * 1000
        if LOG_LEVEL >= 1:
            logger.info(f"Request: {method} {path} | Status: {status} | Duration: {duration_ms:.2f} ms")
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
        """Log a request that resulted in an error."""
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
        """Send metrics to CloudWatch if available."""
        if not self.cloudwatch:
            return
        try:
            self.cloudwatch.put_metric_data(
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
        except Exception:
            logger.debug("CloudWatch put_metric_data failed", exc_info=True)
            self.cloudwatch = None


def setup_logging(app: ASGIApp) -> ASGIApp:
    """Wrap the ASGI app with logging middleware."""
    return LoggingMiddleware(app)
