from __future__ import annotations

import uuid
from typing import Dict, Iterable, List, Optional, cast

from backend.models import (Artifact, ArtifactID, ArtifactMetadata,
                            ArtifactQuery, ArtifactType, ModelRating)
from backend.storage.records import (CodeRecord, DatasetRecord,
                                     LineageMetadata, ModelRecord)

# ---------------------------------------------------------------------------
# In-memory stores separated by artifact type
# ---------------------------------------------------------------------------

_MODELS: Dict[ArtifactID, ModelRecord] = {}
_DATASETS: Dict[ArtifactID, DatasetRecord] = {}
_CODES: Dict[ArtifactID, CodeRecord] = {}

_TYPE_TO_STORE = {
    ArtifactType.MODEL: _MODELS,
    ArtifactType.DATASET: _DATASETS,
    ArtifactType.CODE: _CODES,
}


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def generate_artifact_id() -> ArtifactID:
    return str(uuid.uuid4())


def _get_store(artifact_type: ArtifactType):
    return _TYPE_TO_STORE[artifact_type]


def _find_by_url(artifact_type: ArtifactType, url: str) -> Optional[ArtifactID]:
    store = _get_store(artifact_type)
    for artifact_id, record in store.items():
        if record.artifact.data.url == url:
            return artifact_id
    return None


def _normalized(name: Optional[str]) -> Optional[str]:
    return name.strip().lower() if isinstance(name, str) else None


def _link_dataset_code(model_record: ModelRecord) -> None:
    dataset_name = _normalized(model_record.dataset_name)
    if model_record.dataset_id is None and dataset_name:
        for dataset_id, dataset_record in _DATASETS.items():
            if _normalized(dataset_record.artifact.metadata.name) == dataset_name:
                model_record.dataset_id = dataset_id
                model_record.dataset_url = dataset_record.artifact.data.url
                break

    code_name = _normalized(model_record.code_name)
    if model_record.code_id is None and code_name:
        for code_id, code_record in _CODES.items():
            if _normalized(code_record.artifact.metadata.name) == code_name:
                model_record.code_id = code_id
                model_record.code_url = code_record.artifact.data.url
                break


def _link_base_model(model_record: ModelRecord) -> None:
    """
    Link base model from lineage metadata by finding matching model in registry.
    """
    if not model_record.lineage or not model_record.lineage.base_model_name:
        return

    base_model_name = _normalized(model_record.lineage.base_model_name)
    if model_record.lineage.base_model_id is None and base_model_name:
        for model_id, candidate_record in _MODELS.items():
            candidate_name = _normalized(candidate_record.artifact.metadata.name)
            if candidate_name == base_model_name:
                model_record.lineage.base_model_id = model_id
                break


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def save_artifact(
    artifact: Artifact,
    *,
    rating: Optional[ModelRating] = None,
    license: Optional[str] = None,
    dataset_name: Optional[str] = None,
    dataset_url: Optional[str] = None,
    code_name: Optional[str] = None,
    code_url: Optional[str] = None,
    processing_status: Optional[str] = None,
    lineage: Optional[LineageMetadata] = None,
) -> Artifact:
    """Insert or update an artifact entry in the appropriate store."""
    if artifact.metadata.type == ArtifactType.MODEL:
        record = _MODELS.get(artifact.metadata.id)
        if record:
            record.artifact = artifact
            record.rating = rating or record.rating
            record.dataset_name = dataset_name or record.dataset_name
            record.dataset_url = dataset_url or record.dataset_url
            record.code_name = code_name or record.code_name
            record.code_url = code_url or record.code_url
            record.license = license or record.license
            record.lineage = lineage or record.lineage
            if processing_status is not None:
                record.processing_status = processing_status
        else:
            record = ModelRecord(
                artifact=artifact,
                rating=rating,
                license=license,
                dataset_name=dataset_name,
                dataset_url=dataset_url,
                code_name=code_name,
                code_url=code_url,
                processing_status=processing_status or "completed",
                lineage=lineage,
            )
            _MODELS[artifact.metadata.id] = record
        _link_dataset_code(record)
        _link_base_model(record)
    elif artifact.metadata.type == ArtifactType.DATASET:
        _DATASETS[artifact.metadata.id] = DatasetRecord(artifact=artifact)
        dataset_name_normalized = _normalized(artifact.metadata.name)
        for model_record in _MODELS.values():
            if model_record.dataset_id is None and _normalized(model_record.dataset_name) == dataset_name_normalized:
                model_record.dataset_id = artifact.metadata.id
                model_record.dataset_url = artifact.data.url
    elif artifact.metadata.type == ArtifactType.CODE:
        _CODES[artifact.metadata.id] = CodeRecord(artifact=artifact)
        code_name_normalized = _normalized(artifact.metadata.name)
        for model_record in _MODELS.values():
            if model_record.code_id is None and _normalized(model_record.code_name) == code_name_normalized:
                model_record.code_id = artifact.metadata.id
                model_record.code_url = artifact.data.url
    else:
        raise ValueError(f"Unsupported artifact type: {artifact.metadata.type}")
    return artifact


def get_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> Optional[Artifact]:
    record = _get_store(artifact_type).get(artifact_id)
    if not record:
        return None
    return record.artifact


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    store = _get_store(artifact_type)
    if artifact_id not in store:
        return False

    if artifact_type == ArtifactType.DATASET:
        for model_record in _MODELS.values():
            if model_record.dataset_id == artifact_id:
                model_record.dataset_id = None
                model_record.dataset_url = None
    elif artifact_type == ArtifactType.CODE:
        for model_record in _MODELS.values():
            if model_record.code_id == artifact_id:
                model_record.code_id = None
                model_record.code_url = None

    del store[artifact_id]
    return True


def list_metadata(artifact_type: ArtifactType) -> List[ArtifactMetadata]:
    return [record.artifact.metadata for record in _get_store(artifact_type).values()]


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    results: Dict[str, ArtifactMetadata] = {}
    for query in queries:
        types = query.types or list(_TYPE_TO_STORE.keys())
        for artifact_type in types:
            for record in _get_store(artifact_type).values():
                metadata = record.artifact.metadata

                # FIX: exact match except "*"
                if query.name == "*" or query.name.lower() == metadata.name.lower():
                    results[f"{metadata.type}:{metadata.id}"] = metadata

    return list(results.values())


def reset() -> None:
    for store in _TYPE_TO_STORE.values():
        store = cast(dict[ArtifactID, object], store)
        store.clear()


# ---------------------------------------------------------------------------
# Additional helpers for registration workflow
# ---------------------------------------------------------------------------

def artifact_exists(artifact_type: ArtifactType, url: str) -> bool:
    return _find_by_url(artifact_type, url) is not None


def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    if artifact_id in _MODELS:
        record = _MODELS[artifact_id]
        record.rating = rating


def save_model_license(artifact_id: ArtifactID, license: str) -> None:
    if artifact_id in _MODELS:
        record = _MODELS[artifact_id]
        record.license = license


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.rating


def get_model_license(artifact_id: ArtifactID) -> Optional[str]:
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.license


def get_processing_status(artifact_id: ArtifactID) -> Optional[str]:
    """Get the processing status of a model artifact."""
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.processing_status


def update_processing_status(artifact_id: ArtifactID, status: str) -> None:
    """Update the processing status of a model artifact."""
    record = _MODELS.get(artifact_id)
    if record:
        record.processing_status = status


def find_dataset_by_name(name: str) -> Optional[DatasetRecord]:
    normalized = _normalized(name)
    for record in _DATASETS.values():
        if _normalized(record.artifact.metadata.name) == normalized:
            return record
    return None


def find_code_by_name(name: str) -> Optional[CodeRecord]:
    normalized = _normalized(name)
    for record in _CODES.values():
        if _normalized(record.artifact.metadata.name) == normalized:
            return record
    return None


def get_model_lineage(artifact_id: ArtifactID) -> Optional[LineageMetadata]:
    """Get lineage metadata for a model."""
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.lineage


def find_model_by_name(name: str) -> Optional[ModelRecord]:
    """Find a model by name (case-insensitive)."""
    normalized = _normalized(name)
    for record in _MODELS.values():
        if _normalized(record.artifact.metadata.name) == normalized:
            return record
    return None
