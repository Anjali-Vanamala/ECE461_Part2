import json
import os
import time
import tempfile
from typing import Any, Dict, List, Tuple

# TODO: Add OpenAPI specification (auto-generated or static) for API documentation
# TODO: Add request/response logging for debugging and observability
# TODO: Add error handling and validation for malformed input lines
# TODO: Consider adding API Gateway authentication for production use
# TODO: Add basic CloudWatch metrics and dashboard for monitoring
# TODO: Complete AWS setup: ECR repo, Lambda function, API Gateway, OIDC role [MVP]


def _ok(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _bad_request(message: str) -> Dict[str, Any]:
    return {
        "statusCode": 400,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"error": message}),
    }


def _parse_event(event: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    # Simplified for API Gateway HTTP API (v2) only
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("requestContext", {}).get("http", {}).get("path", "/")
    
    body_raw = event.get("body", "{}")
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
    except Exception:
        body = {}
    
    return method, path, body


def _handle_health() -> Dict[str, Any]:
    return _ok({
        "status": "ok",
        "service": "ece461-part2",
        "region": os.environ.get("AWS_REGION", "us-east-1"),
        "version": os.environ.get("GIT_SHA", "unknown"),
        "time": int(time.time()),
    })


def _handle_rate(payload: Dict[str, Any]) -> Dict[str, Any]:
    lines: List[str] = payload.get("lines", []) if isinstance(payload, dict) else []
    if not lines:
        return _bad_request("Missing 'lines' array of 'code_url,dataset_url,model_url' entries")

    # Write lines to a temp file to reuse the existing CLI flow unmodified
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        for line in lines:
            tf.write(str(line).strip() + "\n")
        tf.flush()

        import sys
        from io import StringIO
        import contextlib
        import input as cli_entry

        original_argv = sys.argv
        sys.argv = ["input.py", tf.name]
        outputs: List[Dict[str, Any]] = []
        try:
            with contextlib.redirect_stdout(StringIO()) as buf:
                cli_entry.main()
                out = buf.getvalue().strip()
                if out:
                    for ln in out.splitlines():
                        try:
                            outputs.append(json.loads(ln))
                        except Exception:
                            pass
        finally:
            sys.argv = original_argv

    return _ok({"results": outputs})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method, path, body = _parse_event(event or {})

    # Simple route matching
    if method == "GET" and path in ("/health", "/"):
        return _handle_health()

    if method == "POST" and path == "/rate":
        return _handle_rate(body)

    return {
        "statusCode": 404,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"error": "Not Found", "method": method, "path": path}),
    }


