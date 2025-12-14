"""
In-memory artifact storage module.

Provides CRUD operations and query utilities for artifacts
(models, datasets, code) using in-memory dictionaries.
Handles artifact linking, lineage resolution, and metadata management.

This module is intended for testing, development, or ephemeral storage
where persistence is not required.
"""
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
    """Generate a new unique artifact ID."""
    return str(uuid.uuid4())


def _get_store(artifact_type: ArtifactType):
    """Get the in-memory store dictionary for the given artifact type."""
    return _TYPE_TO_STORE[artifact_type]


def _find_by_url(artifact_type: ArtifactType, url: str) -> Optional[ArtifactID]:
    """Find an artifact ID by its URL in the specified artifact type store."""
    store = _get_store(artifact_type)
    for artifact_id, record in store.items():
        if record.artifact.data.url == url:
            return artifact_id
    return None


def _normalized(name: Optional[str]) -> Optional[str]:
    """Return normalized (lowercase, stripped) version of name, or None if name is None."""
    return name.strip().lower() if isinstance(name, str) else None


def _link_dataset_code(model_record: ModelRecord) -> None:
    """
    Link dataset and code artifacts by name if IDs are missing."""
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
    Handles both full HuggingFace IDs (namespace/model) and short names (model).
    """
    base_model_name = None
    if model_record.lineage and model_record.lineage.base_model_name:
        base_model_name = model_record.lineage.base_model_name
    elif model_record.base_model_name:
        base_model_name = model_record.base_model_name

    if not base_model_name:
        return

    base_model_name = _normalized(base_model_name)
    if not base_model_name:
        return
    # Extract short name (last part after /) for flexible matching
    base_model_short = base_model_name.split('/')[-1] if '/' in base_model_name else base_model_name

    # Check if already linked (in lineage or directly)
    if (model_record.lineage and model_record.lineage.base_model_id) or model_record.base_model_id:
        return

    for model_id, candidate_record in _MODELS.items():
        candidate_name = _normalized(candidate_record.artifact.metadata.name)
        if not candidate_name:
            continue
        candidate_short = candidate_name.split('/')[-1] if '/' in candidate_name else candidate_name

        # Match on either full name OR short name
        if candidate_name == base_model_name or candidate_short == base_model_short or candidate_name == base_model_short:
            if model_record.lineage:
                model_record.lineage.base_model_id = model_id
            model_record.base_model_id = model_id
            break


def _link_datasets(model_record: ModelRecord) -> None:
    """
    Link datasets from lineage metadata by finding matching datasets in registry.
    Handles both full HuggingFace IDs (namespace/dataset) and short names (dataset).
    """
    if not model_record.lineage or not model_record.lineage.dataset_names:
        return

    # Clear existing dataset_ids to rebuild from scratch
    model_record.lineage.dataset_ids = []

    for dataset_name in model_record.lineage.dataset_names:
        normalized_name = _normalized(dataset_name)
        if not normalized_name:
            continue
        normalized_short = normalized_name.split('/')[-1] if '/' in normalized_name else normalized_name

        # Search for matching dataset in registry
        for dataset_id, dataset_record in _DATASETS.items():
            candidate_name = _normalized(dataset_record.artifact.metadata.name)
            if not candidate_name:
                continue
            candidate_short = candidate_name.split('/')[-1] if '/' in candidate_name else candidate_name

            # Match on either full name OR short name
            if candidate_name == normalized_name or candidate_short == normalized_short or candidate_name == normalized_short:
                model_record.lineage.dataset_ids.append(dataset_id)
                break


def _update_child_models(newly_added_model: ModelRecord) -> None:
    """
    After adding a new model, check if any existing models reference it as a base model.
    This handles the case where child models are ingested before their parent models.
    Handles both full HuggingFace IDs (namespace/model) and short names (model).
    """
    newly_added_name = _normalized(newly_added_model.artifact.metadata.name)
    if not newly_added_name:
        return
    newly_added_short = newly_added_name.split('/')[-1] if '/' in newly_added_name else newly_added_name

    # Check all existing models to see if they reference this new model as a base
    for model_record in _MODELS.values():
        base_model_name = None
        if model_record.lineage and model_record.lineage.base_model_name:
            base_model_name = model_record.lineage.base_model_name
        elif model_record.base_model_name:
            base_model_name = model_record.base_model_name

        if not base_model_name:
            continue

        # If this model was waiting for the newly added model as its base
        normalized_base_name = _normalized(base_model_name)
        if not normalized_base_name:
            continue
        base_model_short = normalized_base_name.split('/')[-1] if '/' in normalized_base_name else normalized_base_name

        # Match on either full name OR short name
        name_matches = newly_added_name == normalized_base_name or newly_added_name == base_model_short
        short_matches = newly_added_short == base_model_short
        if name_matches or short_matches:

            # Check if already linked
            if (model_record.lineage and model_record.lineage.base_model_id is None) or model_record.base_model_id is None:
                if model_record.lineage:
                    model_record.lineage.base_model_id = newly_added_model.artifact.metadata.id
                model_record.base_model_id = newly_added_model.artifact.metadata.id


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
    readme: Optional[str] = None,
    processing_status: Optional[str] = None,
    lineage: Optional[LineageMetadata] = None,
    base_model_name: Optional[str] = None,
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
            record.base_model_name = base_model_name or record.base_model_name
            record.readme = readme or record.readme
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
                base_model_name=base_model_name,
                readme=readme,
                processing_status=processing_status or "completed",
                lineage=lineage,
            )
            _MODELS[artifact.metadata.id] = record
        _link_dataset_code(record)
        _link_base_model(record)
        _link_datasets(record)
        # After adding a new model, check if any EXISTING models reference it as a base model
        _update_child_models(record)
    elif artifact.metadata.type == ArtifactType.DATASET:
        _DATASETS[artifact.metadata.id] = DatasetRecord(artifact=artifact)
        dataset_name_normalized = _normalized(artifact.metadata.name)
        if not dataset_name_normalized:
            return artifact
        dataset_name_short = dataset_name_normalized.split('/')[-1] if '/' in dataset_name_normalized else dataset_name_normalized

        # Update old-style dataset linking for backward compatibility
        for model_record in _MODELS.values():
            if model_record.dataset_id is None and _normalized(model_record.dataset_name) == dataset_name_normalized:
                model_record.dataset_id = artifact.metadata.id
                model_record.dataset_url = artifact.data.url

            # Also update lineage.dataset_ids for any models waiting for this dataset
            if model_record.lineage and model_record.lineage.dataset_names:
                for idx, dataset_name in enumerate(model_record.lineage.dataset_names):
                    normalized = _normalized(dataset_name)
                    if not normalized:
                        continue
                    normalized_short = normalized.split('/')[-1] if '/' in normalized else normalized

                    # Check if this dataset matches and hasn't been linked yet
                    full_name_match = dataset_name_normalized == normalized or dataset_name_normalized == normalized_short
                    short_name_match = dataset_name_short == normalized_short
                    if full_name_match or short_name_match:
                        # Only add if not already in dataset_ids
                        if artifact.metadata.id not in model_record.lineage.dataset_ids:
                            model_record.lineage.dataset_ids.append(artifact.metadata.id)
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
    """Retrieve an artifact by type and ID."""
    record = _get_store(artifact_type).get(artifact_id)
    if not record:
        return None
    return record.artifact


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    """Delete an artifact by type and ID. Returns True if deleted, False if not found."""
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
    """List metadata for all artifacts of the given type."""
    return [record.artifact.metadata for record in _get_store(artifact_type).values()]


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    """Query artifacts based on a list of ArtifactQuery objects."""
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
    """Clear all in-memory stores."""
    for store in _TYPE_TO_STORE.values():
        store = cast(dict[ArtifactID, object], store)
        store.clear()


# ---------------------------------------------------------------------------
# Additional helpers for registration workflow
# ---------------------------------------------------------------------------

def artifact_exists(artifact_type: ArtifactType, url: str) -> bool:
    """Check if an artifact with the given URL exists in the specified type store."""
    return _find_by_url(artifact_type, url) is not None


def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    """Save or update the rating for a model artifact."""
    if artifact_id in _MODELS:
        record = _MODELS[artifact_id]
        record.rating = rating


def save_model_license(artifact_id: ArtifactID, license: str) -> None:
    """Save or update the license for a model artifact."""
    if artifact_id in _MODELS:
        record = _MODELS[artifact_id]
        record.license = license


def save_model_readme(artifact_id: ArtifactID, readme: str) -> None:
    """Save or update the README for a model artifact."""
    if artifact_id in _MODELS:
        record = _MODELS[artifact_id]
        record.readme = readme


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    """Get the rating for a model artifact."""
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.rating


def get_model_license(artifact_id: ArtifactID) -> Optional[str]:
    """Get the license for a model artifact."""
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.license


def get_model_record(artifact_id: ArtifactID) -> Optional[ModelRecord]:
    """Get the ModelRecord for a given artifact ID."""
    return _MODELS.get(artifact_id)


def get_model_readme(artifact_id: ArtifactID) -> Optional[str]:
    """Get the README for a model artifact."""
    record = _MODELS.get(artifact_id)
    if not record:
        return None
    return record.readme


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
    """Find dataset by name with flexible matching (handles namespace/name format)."""
    normalized = _normalized(name)
    if not normalized:
        return None
    normalized_short = normalized.split('/')[-1] if '/' in normalized else normalized

    for record in _DATASETS.values():
        candidate = _normalized(record.artifact.metadata.name)
        if not candidate:
            continue
        candidate_short = candidate.split('/')[-1] if '/' in candidate else candidate

        # Match on either full name OR short name
        if candidate == normalized or candidate_short == normalized_short or candidate == normalized_short:
            return record
    return None


def find_code_by_name(name: str) -> Optional[CodeRecord]:
    """Find code repository by name (case-insensitive)."""
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
    """
    Find a model by name (case-insensitive).
    Handles both full HuggingFace IDs (namespace/model) and short names (model).
    """
    normalized = _normalized(name)
    if not normalized:
        return None
    normalized_short = normalized.split('/')[-1] if '/' in normalized else normalized

    for record in _MODELS.values():
        candidate = _normalized(record.artifact.metadata.name)
        if not candidate:
            continue
        candidate_short = candidate.split('/')[-1] if '/' in candidate else candidate

        # Match on either full name OR short name
        if candidate == normalized or candidate_short == normalized_short or candidate == normalized_short:
            return record
    return None


def find_child_models(parent_model_id: ArtifactID) -> List[ModelRecord]:
    """
    Find all models that use the given model as their base model.
    Returns list of ModelRecords that have this model as their parent.
    """
    children = []
    for record in _MODELS.values():
        # Check if this model's base_model_id matches the parent
        if record.base_model_id == parent_model_id:
            children.append(record)
        # Also check lineage.base_model_id
        elif record.lineage and record.lineage.base_model_id == parent_model_id:
            children.append(record)
    return children
