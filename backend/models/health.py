from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

HealthMetricValue = Union[int, float, str, bool]
HealthMetricMap = Dict[str, HealthMetricValue]


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthTimelineEntry(BaseModel):
    bucket: datetime = Field(..., description="Start timestamp of the sampled bucket (UTC)")
    value: float = Field(..., description="Observed value for the bucket")
    unit: Optional[str] = Field(None, description="Unit associated with the metric value")


class HealthIssue(BaseModel):
    code: str = Field(..., description="Machine readable issue identifier")
    severity: str = Field(..., description="Issue severity", pattern="^(info|warning|error)$")
    summary: str = Field(..., description="Short description of the issue")
    details: Optional[str] = Field(None, description="Extended diagnostic detail and suggested remediation")


class HealthLogReference(BaseModel):
    label: str = Field(..., description="Human readable log descriptor")
    url: str = Field(..., description="Direct link to download or tail the referenced log")
    tail_available: Optional[bool] = Field(None, description="Indicates whether streaming tail access is supported")
    last_updated_at: Optional[datetime] = Field(None, description="Timestamp of the latest log entry")


class HealthComponentBrief(BaseModel):
    id: str = Field(..., description="Stable identifier for the component")
    display_name: Optional[str] = Field(None, description="Human readable component name")
    status: HealthStatus = Field(..., description="Component status")
    issue_count: Optional[int] = Field(None, ge=0, description="Number of outstanding issues")
    last_event_at: Optional[datetime] = Field(None, description="Last significant event timestamp")


class HealthComponentDetail(BaseModel):
    id: str = Field(..., description="Stable identifier for the component")
    display_name: Optional[str] = Field(None, description="Human readable component name")
    status: HealthStatus = Field(..., description="Component status")
    observed_at: datetime = Field(..., description="Timestamp when data was last collected")
    description: Optional[str] = Field(None, description="Overview of the component's responsibility")
    metrics: Optional[HealthMetricMap] = Field(None, description="Metric key/value pairs describing performance")
    issues: Optional[List[HealthIssue]] = Field(None, description="Outstanding issues or alerts")
    timeline: Optional[List[HealthTimelineEntry]] = Field(None, description="Time-series datapoints for component metrics")
    logs: Optional[List[HealthLogReference]] = Field(None, description="Relevant log references")


class HealthRequestSummary(BaseModel):
    window_start: datetime = Field(..., description="Beginning of the aggregation window (UTC)")
    window_end: datetime = Field(..., description="End of the aggregation window (UTC)")
    total_requests: Optional[int] = Field(None, ge=0, description="Number of API requests served during the window")
    per_route: Optional[Dict[str, int]] = Field(None, description="Request counts grouped by API route")
    per_artifact_type: Optional[Dict[str, int]] = Field(None, description="Request counts grouped by artifact type")
    unique_clients: Optional[int] = Field(None, ge=0, description="Distinct API clients observed in the window")


class HealthComponentCollection(BaseModel):
    components: List[HealthComponentDetail] = Field(..., description="Detailed diagnostics per component")
    generated_at: datetime = Field(..., description="Timestamp when the report was created (UTC)")
    window_minutes: int = Field(..., ge=5, description="Observation window applied to the component metrics")


class HealthSummaryResponse(BaseModel):
    status: HealthStatus = Field(..., description="Aggregate health classification")
    checked_at: datetime = Field(..., description="Timestamp when the health snapshot was generated (UTC)")
    window_minutes: int = Field(..., ge=5, description="Size of the trailing observation window in minutes")
    uptime_seconds: Optional[int] = Field(None, ge=0, description="Seconds the registry API has been running")
    version: Optional[str] = Field(None, description="Running service version or git SHA")
    request_summary: Optional[HealthRequestSummary] = Field(None, description="Request activity observed within the window")
    components: Optional[List[HealthComponentBrief]] = Field(None, description="Rollup of component status ordered by severity")
    logs: Optional[List[HealthLogReference]] = Field(None, description="Quick links or descriptors for recent log files")


__all__ = [
    "HealthStatus",
    "HealthTimelineEntry",
    "HealthIssue",
    "HealthLogReference",
    "HealthComponentBrief",
    "HealthComponentDetail",
    "HealthRequestSummary",
    "HealthComponentCollection",
    "HealthSummaryResponse",
    "HealthMetricValue",
    "HealthMetricMap",
]
