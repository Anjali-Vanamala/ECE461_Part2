from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.models import Artifact, ArtifactID, ModelRating


@dataclass
class LineageMetadata:
    """Stores lineage information extracted from model metadata."""
    base_model_name: Optional[str] = None
    base_model_id: Optional[ArtifactID] = None
    dataset_names: List[str] = field(default_factory=list)
    dataset_ids: List[ArtifactID] = field(default_factory=list)
    config_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ModelRecord:
    artifact: Artifact
    dataset_id: Optional[ArtifactID] = None
    dataset_name: Optional[str] = None
    dataset_url: Optional[str] = None
    code_id: Optional[ArtifactID] = None
    code_name: Optional[str] = None
    code_url: Optional[str] = None
    base_model_id: Optional[ArtifactID] = None
    base_model_name: Optional[str] = None
    rating: Optional[ModelRating] = None
    license: Optional[str] = None
    readme: Optional[str] = None
    processing_status: str = "completed"  # "processing", "completed", "failed"
    lineage: Optional[LineageMetadata] = None


@dataclass
class DatasetRecord:
    artifact: Artifact


@dataclass
class CodeRecord:
    artifact: Artifact
