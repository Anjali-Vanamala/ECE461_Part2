from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SizeScore(BaseModel):
    """Size score with value and unit"""
    value: float
    unit: str


class PackageCreate(BaseModel):
    """Request model for creating a package"""
    URL: str = Field(..., description="HuggingFace model URL")


class PackageUpdate(BaseModel):
    """Request model for updating a package (all fields optional)"""
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class PackageModel(BaseModel):
    """Full package model with all metrics"""
    # Core fields
    id: str = Field(..., description="Unique package identifier")
    name: str = Field(..., description="Package name")
    category: str = Field(default="MODEL", description="Package category")
    URL: str = Field(..., description="Original URL")
    description: Optional[str] = Field(None, description="Package description")

    # Metric scores (0-1 range)
    net_score: float = Field(..., ge=0, le=1, description="Overall net score")
    ramp_up_time: float = Field(..., ge=0, le=1)
    bus_factor: float = Field(..., ge=0, le=1)
    performance_claims: float = Field(..., ge=0, le=1)
    license: float = Field(..., ge=0, le=1)
    dataset_and_code_score: float = Field(..., ge=0, le=1)
    dataset_quality: float = Field(..., ge=0, le=1)
    code_quality: float = Field(..., ge=0, le=1)
    reproducibility: float = Field(..., ge=0, le=1)
    reviewedness: float = Field(..., ge=0, le=1)
    treescore: float = Field(..., ge=0, le=1)
    size_score: Dict[str, Any] = Field(..., description="Size score dictionary with value and unit")

    # Latencies (milliseconds)
    net_score_latency: int = Field(..., ge=0)
    ramp_up_time_latency: int = Field(..., ge=0)
    bus_factor_latency: int = Field(..., ge=0)
    performance_claims_latency: int = Field(..., ge=0)
    license_latency: int = Field(..., ge=0)
    size_score_latency: int = Field(..., ge=0)
    dataset_and_code_score_latency: int = Field(..., ge=0)
    dataset_quality_latency: int = Field(..., ge=0)
    code_quality_latency: int = Field(..., ge=0)
    reproducibility_latency: int = Field(..., ge=0)
    reviewedness_latency: int = Field(..., ge=0)
    treescore_latency: int = Field(..., ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "bert-base-uncased",
                "name": "bert-base-uncased",
                "category": "MODEL",
                "URL": "https://huggingface.co/google/bert-base-uncased",
                "net_score": 0.85,
                "ramp_up_time": 0.8,
                "bus_factor": 0.9
            }
        }


class PackageListResponse(BaseModel):
    """Response model for listing packages"""
    items: list[PackageModel]
    total: int
    offset: int
    limit: int
