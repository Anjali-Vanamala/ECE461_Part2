"""Middleware for logging HTTP requests and CloudWatch metrics."""
import json
import os
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import logger

try:
    import boto3
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs requests/errors and publishes CloudWatch metrics."""

    def __init__(self, app):
        super().__init__(app)
        self.cloudwatch = None
        if CLOUDWATCH_AVAILABLE:
            try:
                self.cloudwatch = boto3.client(
                    'cloudwatch',
                    region_name=os.environ.get('AWS_REGION', 'us-east-2')
                )
            except Exception:
                # Silently fail - CloudWatch is optional
                pass

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            latency_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                f"Request: {method} {path} | Status: {response.status_code} | "
                f"Latency: {latency_ms}ms | IP: {client_ip}"
            )

            self._log_debug("request", method, path, response.status_code, latency_ms, client_ip)
            self._send_metrics(method, path, latency_ms, status_code=response.status_code)

            return response

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                f"Error: {method} {path} | {str(e)} | Type: {type(e).__name__} | "
                f"Latency: {latency_ms}ms | IP: {client_ip}"
            )

            self._log_debug("error", method, path, type(e).__name__, latency_ms, client_ip, str(e))
            self._send_metrics(method, path, latency_ms, error_type=type(e).__name__)

            raise

    def _log_debug(self, log_type, method, path, status_or_error, latency_ms, client_ip, error_msg=None):
        if os.environ.get('LOG_LEVEL') != '2':
            return

        data = {
            "type": log_type,
            "method": method,
            "path": path,
            "latency_ms": latency_ms,
            "client_ip": client_ip
        }

        if log_type == "error":
            data["error_type"] = status_or_error
            data["error"] = error_msg
        else:
            data["status_code"] = status_or_error

        logger.debug(json.dumps(data))

    def _send_metrics(self, method, path, latency_ms, status_code=None, error_type=None):
        if not self.cloudwatch:
            return

        try:
            metrics = [{
                'MetricName': 'APILatency',
                'Value': latency_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Path', 'Value': path},
                    {'Name': 'Method', 'Value': method}
                ]
            }]

            if error_type:
                metrics.append({
                    'MetricName': 'ErrorCount',
                    'Value': 1.0,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Path', 'Value': path},
                        {'Name': 'Method', 'Value': method},
                        {'Name': 'ErrorType', 'Value': error_type}
                    ]
                })
            else:
                metrics.append({
                    'MetricName': 'RequestCount',
                    'Value': 1.0,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Method', 'Value': method},
                        {'Name': 'Path', 'Value': path},
                        {'Name': 'StatusCode', 'Value': str(status_code)}
                    ]
                })

            self.cloudwatch.put_metric_data(Namespace='ECE461/API', MetricData=metrics)
        except Exception:
            # Silently fail - CloudWatch metrics are non-critical
            pass
