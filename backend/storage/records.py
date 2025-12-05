from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.models import Artifact, ArtifactID, ModelRating


@dataclass
class ModelRecord:
    artifact: Artifact
    dataset_id: Optional[ArtifactID] = None
    dataset_name: Optional[str] = None
    dataset_url: Optional[str] = None
    code_id: Optional[ArtifactID] = None
    code_name: Optional[str] = None
    code_url: Optional[str] = None
    rating: Optional[ModelRating] = None,
    license: Optional[str] = None

@dataclass
class DatasetRecord:
    artifact: Artifact


@dataclass
class CodeRecord:
    artifact: Artifact
