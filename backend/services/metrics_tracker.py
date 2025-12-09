"""
In-memory metrics tracker for health monitoring.
Tracks requests, uptime, and system metrics.
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

# Global state
_start_time = time.time()
_request_log: List[Dict[str, Any]] = []
_client_ips: Set[str] = set()


def record_request(
    method: str,
    path: str,
    status_code: int,
    client_ip: Optional[str] = None,
    artifact_type: Optional[str] = None,
) -> None:
    """Record a request for metrics tracking."""
    now = datetime.now(timezone.utc)
    _request_log.append({
        "timestamp": now,
        "method": method,
        "path": path,
        "status_code": status_code,
        "client_ip": client_ip,
    })

    if client_ip:
        _client_ips.add(client_ip)

    # Keep only last 24 hours of requests to avoid memory issues
    cutoff = now - timedelta(hours=24)
    _request_log[:] = [req for req in _request_log if req["timestamp"] > cutoff]


def get_uptime_seconds() -> int:
    """Get uptime in seconds since server started."""
    return int(time.time() - _start_time)


def get_request_summary(window_minutes: int = 60) -> Dict[str, Any]:
    """Get request summary for the specified time window."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)

    # Filter requests in window
    window_requests = [
        req for req in _request_log
        if req["timestamp"] >= window_start
    ]

    # Count by route
    per_route: Dict[str, int] = defaultdict(int)
    per_artifact_type: Dict[str, int] = defaultdict(int)

    for req in window_requests:
        # Extract route pattern (remove IDs, query params)
        path = req["path"]
        # Simplify paths like /artifacts/model/{id} to /artifacts/model
        route_parts = path.split("/")
        if len(route_parts) > 3 and route_parts[1] == "artifacts":
            # Keep artifact type but remove ID
            route = f"/{route_parts[1]}/{route_parts[2]}"
        else:
            route = "/".join(route_parts[:3]) if len(route_parts) >= 3 else path.split("?")[0]

        per_route[route] += 1

        # Try to extract artifact type from path
        if "/artifacts/" in path:
            parts = path.split("/artifacts/")
            if len(parts) > 1:
                artifact_type = parts[1].split("/")[0]
                per_artifact_type[artifact_type] += 1

    # Count unique clients in window
    window_client_ips = {
        req.get("client_ip")
        for req in window_requests
        if req.get("client_ip")
    }

    return {
        "window_start": window_start,
        "window_end": now,
        "total_requests": len(window_requests),
        "per_route": dict(per_route),
        "per_artifact_type": dict(per_artifact_type),
        "unique_clients": len(window_client_ips),
    }


def get_requests_per_minute(window_minutes: int = 60) -> float:
    """Calculate average requests per minute in the window."""
    summary = get_request_summary(window_minutes)
    if window_minutes == 0:
        return 0.0
    return summary["total_requests"] / window_minutes


def get_timeline(window_minutes: int = 60, buckets: int = 10) -> List[Dict[str, Any]]:
    """Get timeline data for the window."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)

    window_requests = [
        req for req in _request_log
        if req["timestamp"] >= window_start
    ]

    if not window_requests:
        return []

    # Create buckets
    bucket_size_minutes = window_minutes / buckets
    timeline = []

    for i in range(buckets):
        bucket_start = window_start + timedelta(minutes=i * bucket_size_minutes)
        bucket_end = bucket_start + timedelta(minutes=bucket_size_minutes)

        bucket_requests = [
            req for req in window_requests
            if bucket_start <= req["timestamp"] < bucket_end
        ]

        # Calculate requests per minute for this bucket
        if bucket_size_minutes > 0:
            req_per_min = len(bucket_requests) / bucket_size_minutes
        else:
            req_per_min = 0

        timeline.append({
            "bucket": bucket_start,
            "value": round(req_per_min, 2),
            "unit": "req/min",
        })

    return timeline
