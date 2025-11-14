from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from backend.models import (HealthComponentBrief, HealthComponentCollection,
                            HealthComponentDetail, HealthIssue,
                            HealthLogReference, HealthRequestSummary,
                            HealthStatus, HealthSummaryResponse,
                            HealthTimelineEntry)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Heartbeat check (BASELINE)")
async def health_summary() -> HealthSummaryResponse:
    now = datetime.now(timezone.utc)
    summary = HealthSummaryResponse(
        status=HealthStatus.OK,
        checked_at=now,
        window_minutes=60,
        uptime_seconds=0,
        version="0.0.0",
        request_summary=HealthRequestSummary(
            window_start=now - timedelta(minutes=60),
            window_end=now,
            total_requests=0,
            per_route={},
            per_artifact_type={},
            unique_clients=0,
        ),
        components=[
            HealthComponentBrief(
                id="api",
                status=HealthStatus.OK,
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
    detail = HealthComponentDetail(
        id="api",
        display_name="API Service",
        status=HealthStatus.OK,
        observed_at=now,
        description="Main API service handling requests.",
        metrics={"requests_per_minute": 10},
        issues=[
            HealthIssue(code="none", severity="info", summary="No issues", details=None),
        ],
        timeline=[
            HealthTimelineEntry(bucket=now, value=10, unit="req/min")
        ]
        if include_timeline
        else [],
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
