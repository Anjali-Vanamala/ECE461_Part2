"""
Pydantic models for size-cost analysis.
"""
from typing import Optional

from pydantic import BaseModel, Field


class SizeCostRequest(BaseModel):
    package_id: str = Field(..., description="Package ID to check")
    deployment_target: str = Field(..., description="Deployment target: raspberry_pi, jetson_nano, desktop_pc, or aws_server")
    threshold: Optional[float] = Field(0.7, ge=0, le=1, description="Minimum acceptable size score (default: 0.7)")


class SizeCostResponse(BaseModel):
    package_id: str
    package_name: str
    deployment_target: str
    size_score: float = Field(..., ge=0, le=1)
    threshold: float
    meets_requirement: bool
    recommendation: str


