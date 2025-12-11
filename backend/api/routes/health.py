from datetime import datetime, timezone

from fastapi import APIRouter, Query

from backend.models import (HealthComponentBrief, HealthComponentCollection,
                            HealthComponentDetail, HealthIssue,
                            HealthLogReference, HealthRequestSummary,
                            HealthStatus, HealthSummaryResponse,
                            HealthTimelineEntry)
from backend.services.metrics_tracker import (get_request_summary,
                                              get_requests_per_minute,
                                              get_timeline, get_uptime_seconds)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Heartbeat check (BASELINE)")
async def health_summary() -> HealthSummaryResponse:
    now = datetime.now(timezone.utc)
    window_minutes = 60

    # Get real request summary
    request_summary_data = get_request_summary(window_minutes)
    request_summary = HealthRequestSummary(
        window_start=request_summary_data["window_start"],
        window_end=request_summary_data["window_end"],
        total_requests=request_summary_data["total_requests"],
        per_route=request_summary_data["per_route"],
        per_artifact_type=request_summary_data["per_artifact_type"],
        unique_clients=request_summary_data["unique_clients"],
    )

    # Determine overall status (OK if no errors in recent requests)
    # You can make this more sophisticated
    status = HealthStatus.OK

    summary = HealthSummaryResponse(
        status=status,
        checked_at=now,
        window_minutes=window_minutes,
        uptime_seconds=get_uptime_seconds(),
        version="0.1.0",
        request_summary=request_summary,
        components=[
            HealthComponentBrief(
                id="api",
                status=status,
                display_name="API Service",
                issue_count=0,
                last_event_at=now,
            )
        ],
        logs=[],
    )
    return summary


@router.get(
    "/health/components",
    summary="Get component health details (NON-BASELINE)",
)
async def health_components(
    window_minutes: int = Query(60, ge=5, le=1440),
    include_timeline: bool = Query(False),
) -> HealthComponentCollection:
    now = datetime.now(timezone.utc)

    # Get real metrics
    requests_per_min = get_requests_per_minute(window_minutes)
    timeline_data = get_timeline(window_minutes) if include_timeline else []

    # Determine status based on metrics
    status = HealthStatus.OK
    if requests_per_min == 0 and window_minutes >= 60:
        # No requests in last hour might indicate an issue
        status = HealthStatus.DEGRADED

    timeline = [
        HealthTimelineEntry(
            bucket=entry["bucket"],
            value=entry["value"],
            unit=entry["unit"],
        )
        for entry in timeline_data
    ]

    detail = HealthComponentDetail(
        id="api",
        display_name="API Service",
        status=status,
        observed_at=now,
        description="Main API service handling requests.",
        metrics={
            "requests_per_minute": round(requests_per_min, 2),
            "uptime_hours": round(get_uptime_seconds() / 3600, 2),
        },
        issues=[
            HealthIssue(
                code="none", severity="info", summary="No issues", details=None
            ),
        ],
        timeline=timeline,
        logs=[
            HealthLogReference(
                label="API Access",
                url="http://example.com/logs/api_access",
                tail_available=True,
                last_updated_at=now,
            )
        ],
    )
    return HealthComponentCollection(
        components=[detail],
        generated_at=now,
        window_minutes=window_minutes,
    )
