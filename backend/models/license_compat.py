"""
Pydantic models for license compatibility checks.
"""
from typing import Optional

from pydantic import BaseModel, Field


class LicenseCompatRequest(BaseModel):
    package_id: str = Field(..., description="Package ID to check")
    target_license: str = Field(..., description="Target license to check compatibility against (e.g., MIT, Apache-2.0, GPL, BSD)")
    threshold: Optional[float] = Field(0.5, ge=0, le=1, description="Minimum acceptable compatibility score (default: 0.5)")


class LicenseCompatResponse(BaseModel):
    package_id: str
    package_name: str
    package_license: str
    target_license: str
    compatibility_score: float = Field(..., ge=0, le=1)
    threshold: float
    is_compatible: bool
    recommendation: str
