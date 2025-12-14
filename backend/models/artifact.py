"""
Pydantic models for artifacts, artifact metadata, lineage, licensing,
costs, and ratings used throughout the backend system.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, RootModel

ArtifactID = Annotated[
    str,
    Field(
        pattern=r"^[a-zA-Z0-9\-]+$",
        description="Unique identifier for use with artifact endpoints",
    ),
]
ArtifactName = Annotated[
    str,
    Field(description="Name of the artifact"),
]


class ArtifactRegistration(BaseModel):
    """Model registration information including"""
    name: Optional[str] = None
    url: str
    download_url: Optional[str] = None


class ArtifactType(str, Enum):
    """Enumeration of artifact types."""
    MODEL = "model"
    DATASET = "dataset"
    CODE = "code"


class ArtifactMetadata(BaseModel):
    """Metadata for an artifact."""
    name: ArtifactName
    id: ArtifactID
    type: ArtifactType


class ArtifactData(BaseModel):
    """Data related to an artifact."""
    url: str
    download_url: Optional[str] = None


class Artifact(BaseModel):
    """Comprehensive artifact model."""
    metadata: ArtifactMetadata
    data: ArtifactData


class ArtifactQuery(BaseModel):
    """Query parameters for searching artifacts."""
    name: ArtifactName
    types: Optional[List[ArtifactType]] = None


class ArtifactRegEx(BaseModel):
    """Regular expression for artifact name matching."""
    regex: str


class ArtifactCostEntry(BaseModel):
    """Cost details for an artifact."""
    standalone_cost: Optional[float] = None
    total_cost: float


class ArtifactCost(RootModel[Dict[ArtifactID, ArtifactCostEntry]]):
    """Mapping of artifact IDs to their cost entries."""
    pass


class AuditUser(BaseModel):
    """User information for audit entries."""
    name: str
    is_admin: bool


class ArtifactAuditEntry(BaseModel):
    """Audit entry for artifact actions."""
    user: AuditUser
    date: datetime
    artifact: ArtifactMetadata
    action: Literal["CREATE", "UPDATE", "DOWNLOAD", "RATE", "AUDIT"]


class ArtifactLineageNode(BaseModel):
    """Node in the artifact lineage graph."""
    artifact_id: ArtifactID
    name: ArtifactName
    source: str
    metadata: Optional[Dict[str, str]] = None


class ArtifactLineageEdge(BaseModel):
    """Edge in the artifact lineage graph."""
    from_node_artifact_id: ArtifactID
    to_node_artifact_id: ArtifactID
    relationship: str


class ArtifactLineageGraph(BaseModel):
    """Lineage graph for an artifact."""
    nodes: List[ArtifactLineageNode]
    edges: List[ArtifactLineageEdge]


class SimpleLicenseCheckRequest(BaseModel):
    """Request model for simple license checking."""
    github_url: str


class SizeScore(BaseModel):
    """Size score breakdown for different deployment targets."""
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelLicense(BaseModel):
    """Model license information."""
    license_name: Optional[str] = None


class ModelRating(BaseModel):
    """Model rating and various metric scores."""
    name: ArtifactName
    category: str
    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: SizeScore
    size_score_latency: float


__all__ = [
    "Artifact",
    "ArtifactAuditEntry",
    "ArtifactCost",
    "ArtifactCostEntry",
    "ArtifactData",
    "ArtifactID",
    "ArtifactLineageEdge",
    "ArtifactLineageGraph",
    "ArtifactLineageNode",
    "ArtifactMetadata",
    "ArtifactName",
    "ArtifactQuery",
    "ArtifactRegEx",
    "ArtifactType",
    "ModelRating",
    "SimpleLicenseCheckRequest",
]
