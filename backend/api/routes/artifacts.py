from __future__ import annotations

import re
import time
from typing import List

import regex
from fastapi import (APIRouter, Body, HTTPException, Path, Query, Response,
                     status)

from backend.models import (Artifact, ArtifactCost, ArtifactCostEntry,
                            ArtifactData, ArtifactID, ArtifactLineageEdge,
                            ArtifactLineageGraph, ArtifactLineageNode,
                            ArtifactMetadata, ArtifactQuery,
                            ArtifactRegistration, ArtifactType, ModelRating)
from backend.services.rating_service import compute_model_artifact
from backend.storage import memory

router = APIRouter(tags=["artifacts"])


def _derive_name(url: str) -> str:
    stripped = url.strip().rstrip("/")
    if not stripped:
        return "artifact"
    return stripped.split("/")[-1]


router = APIRouter(tags=["artifacts"])


def calibrate_regex_timeout() -> float:
    """
    Measures how long regex takes in this platform for a safe case.
    The timeout is set to 2x the baseline to avoid false-positive timeouts.
    """
    test_pattern = r"a+"
    test_text = "a" * 5000

    start = time.perf_counter()
    regex.search(test_pattern, test_text)
    baseline = time.perf_counter() - start

    # Never allow insanely tiny values
    return max(0.0001, baseline * 2)


# Compute once at import time
REGEX_TIMEOUT = calibrate_regex_timeout()
print(f"[Regex] Calibrated REGEX_TIMEOUT = {REGEX_TIMEOUT:.6f} seconds")


def safe_regex_search(pattern: str, text: str, timeout: float = REGEX_TIMEOUT):
    try:
        return bool(regex.search(pattern, text, timeout=timeout))
    except TimeoutError:
        return None


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def regex_artifact_search(payload: dict = Body(...)):
    if not payload or "regex" not in payload:
        raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")

    regex_str = payload["regex"]

    if not isinstance(regex_str, str) or not regex_str.strip():
        raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")

    try:
        re.compile(regex_str)
    except re.error:
        raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")

    results: List[ArtifactMetadata] = []

    # Initial catastrophic check
    initial_test = safe_regex_search(regex_str, "a" * 5000)
    if initial_test is None:
        raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")

    for store in memory._TYPE_TO_STORE.values():
        for record in store.values():  # type: ignore[attr-defined]
            name = record.artifact.metadata.name
            test = safe_regex_search(regex_str, name)
            if test is None:
                raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")
            if test:
                results.append(record.artifact.metadata)

    if not results:
        raise HTTPException(404, "No artifact found under this regex.")

    return results


@router.post(
    "/artifacts",
    response_model=List[ArtifactMetadata],
    summary="Get the artifacts from the registry. (BASELINE)",
)
async def query_artifacts_endpoint(
    queries: List[ArtifactQuery],
    response: Response,
    offset: int = Query(0, ge=0, description="Pagination offset for the results"),
) -> List[ArtifactMetadata]:
    if not queries:
        raise HTTPException(status_code=400, detail="At least one artifact query is required")

    results = memory.query_artifacts(queries)

    if offset >= len(results):
        response.headers["offset"] = str(offset)
        return []

    paginated = results[offset:]
    next_offset = offset + len(paginated)
    response.headers["offset"] = str(next_offset)
    return paginated


@router.delete("/reset", summary="Reset the registry. (BASELINE)")
async def reset_registry() -> dict[str, str]:
    memory.reset()
    return {"status": "reset"}


@router.post(
    "/artifact/{artifact_type}",
    response_model=Artifact,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new artifact. (BASELINE)",
)
async def register_artifact(
    payload: ArtifactRegistration,
    artifact_type: ArtifactType = Path(..., description="Type of artifact being ingested."),
) -> Artifact:
    if memory.artifact_exists(artifact_type, payload.url):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Artifact exists already")

    if artifact_type == ArtifactType.MODEL:
        try:
            artifact, rating, dataset_name, dataset_url, code_name, code_url = compute_model_artifact(payload.url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc)) from exc

        if payload.name:
            artifact.metadata.name = payload.name

        memory.save_artifact(
            artifact,
            rating=rating,
            dataset_name=dataset_name,
            dataset_url=dataset_url,
            code_name=code_name,
            code_url=code_url,
        )
        if rating:
            memory.save_model_rating(artifact.metadata.id, rating)
        return artifact

    artifact_name = payload.name or _derive_name(payload.url)

    artifact_id = memory.generate_artifact_id()
    artifact = Artifact(
        metadata=ArtifactMetadata(
            name=artifact_name,
            id=artifact_id,
            type=artifact_type,
        ),
        data=ArtifactData(url=payload.url),
    )
    memory.save_artifact(artifact)
    return artifact


@router.get(
    "/artifacts/{artifact_type}/{artifact_id:path}",
    response_model=Artifact,
    summary="Interact with the artifact with this id. (BASELINE)",
    responses={
        400: {"description": "Malformed artifact_type or artifact_id."},
        404: {"description": "Artifact does not exist."},
        200: {"description": "Artifact retrieved successfully."},
    },
)
async def get_artifact(
    artifact_type: str = Path(...),
    artifact_id: str = Path(...),
):
    # 400 — invalid or missing type
    try:
        artifact_type_enum = ArtifactType(artifact_type)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="400: There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.",
        )

    # 400 — invalid or malformed id (UUID)
    import re

    id_pattern = r"^[a-zA-Z0-9\-]+$"

    if not re.fullmatch(id_pattern, artifact_id):
        raise HTTPException(
            status_code=400,
            detail="400: There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.",
        )

    # 404 — not found
    artifact_type_enum = ArtifactType(artifact_type.lower())
    artifact = memory.get_artifact(artifact_type_enum, artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=404,
            detail="404: Artifact does not exist.",
        )

    return artifact


@router.put(
    "/artifacts/{artifact_type}/{artifact_id}",
    response_model=Artifact,
    summary="Update this content of the artifact. (BASELINE)",
)
async def update_artifact(
    payload: Artifact,
    artifact_type: ArtifactType = Path(..., description="Type of artifact to update"),
    artifact_id: ArtifactID = Path(..., description="artifact id"),
) -> Artifact:
    if payload.metadata.id != artifact_id or payload.metadata.type != artifact_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not match path parameters",
        )

    if artifact_type == ArtifactType.MODEL:
        try:
            artifact, rating, dataset_name, dataset_url, code_name, code_url = compute_model_artifact(
                payload.data.url, artifact_id=artifact_id, name_override=payload.metadata.name
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc)) from exc

        memory.save_artifact(
            artifact,
            rating=rating,
            dataset_name=dataset_name,
            dataset_url=dataset_url,
            code_name=code_name,
            code_url=code_url,
        )
        if rating:
            memory.save_model_rating(artifact_id, rating)
        return artifact

    existing = memory.get_artifact(artifact_type, artifact_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist.")

    memory.save_artifact(payload)
    return payload


@router.delete(
    "/artifacts/{artifact_type}/{artifact_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete this artifact. (NON-BASELINE)",
)
async def delete_artifact(
    artifact_type: ArtifactType = Path(..., description="Artifact type"),
    artifact_id: ArtifactID = Path(..., description="Artifact id"),
) -> dict[str, ArtifactID]:
    success = memory.delete_artifact(artifact_type, artifact_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist.")
    return {"deleted": artifact_id}


@router.get(
    "/artifact/model/{artifact_id}/rate",
    response_model=ModelRating,
    summary="Get ratings for this model artifact. (BASELINE)",
)
async def get_model_rating(
    artifact_id: ArtifactID = Path(..., description="Artifact id"),
) -> ModelRating:
    rating = memory.get_model_rating(artifact_id)
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist or lacks a rating.")
    return rating


@router.get(
    "/artifact/model/{artifact_id}/lineage",
    response_model=ArtifactLineageGraph,
    summary="Retrieve the lineage graph for this artifact. (BASELINE)",
    responses={
        400: {"description": "The lineage graph cannot be computed because the artifact metadata is missing or malformed."},
        404: {"description": "Artifact does not exist."},
    },
)
async def get_model_lineage(
    artifact_id: ArtifactID = Path(..., description="Artifact id"),
) -> ArtifactLineageGraph:
    """Get the lineage graph for a model artifact showing its dependencies."""
    # Get model record with relationships
    model_record = memory.get_model_record(artifact_id)
    if not model_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist.")

    nodes: List[ArtifactLineageNode] = []
    edges: List[ArtifactLineageEdge] = []

    # Add model node
    model_node = ArtifactLineageNode(
        artifact_id=model_record.artifact.metadata.id,
        name=model_record.artifact.metadata.name,
        source="model_metadata",
        metadata={"type": "model"},
    )
    nodes.append(model_node)

    # Add dataset node and edge if dataset exists
    if model_record.dataset_id:
        dataset = memory.get_artifact(ArtifactType.DATASET, model_record.dataset_id)
        if dataset:
            dataset_node = ArtifactLineageNode(
                artifact_id=dataset.metadata.id,
                name=dataset.metadata.name,
                source="model_metadata",
                metadata={"type": "dataset"},
            )
            nodes.append(dataset_node)

            # Edge: dataset -> model (dataset is upstream dependency)
            dataset_edge = ArtifactLineageEdge(
                from_node_artifact_id=dataset.metadata.id,
                to_node_artifact_id=model_record.artifact.metadata.id,
                relationship="training_dataset",
            )
            edges.append(dataset_edge)

    # Add code node and edge if code exists
    if model_record.code_id:
        code = memory.get_artifact(ArtifactType.CODE, model_record.code_id)
        if code:
            code_node = ArtifactLineageNode(
                artifact_id=code.metadata.id,
                name=code.metadata.name,
                source="model_metadata",
                metadata={"type": "code"},
            )
            nodes.append(code_node)

            # Edge: code -> model (code is upstream dependency)
            code_edge = ArtifactLineageEdge(
                from_node_artifact_id=code.metadata.id,
                to_node_artifact_id=model_record.artifact.metadata.id,
                relationship="implemented_with",
            )
            edges.append(code_edge)

    return ArtifactLineageGraph(nodes=nodes, edges=edges)


@router.get(
    "/artifact/{artifact_type}/{artifact_id}/cost",
    response_model=ArtifactCost,
    summary="Get the cost of an artifact (BASELINE)",
)
async def get_artifact_cost(
    artifact_type: ArtifactType = Path(..., description="Artifact type"),
    artifact_id: ArtifactID = Path(..., description="Artifact id"),
) -> ArtifactCost:
    artifact = memory.get_artifact(artifact_type, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist.")

    if artifact_type == ArtifactType.MODEL:
        rating = memory.get_model_rating(artifact_id)
        if not rating:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost unavailable until model is rated.",
            )
        total_cost = max(
            0.0,
            round((1.0 - rating.size_score.raspberry_pi) * 1000, 1),
        )
        entry = ArtifactCostEntry(standalone_cost=total_cost, total_cost=total_cost)

    else:
        entry = ArtifactCostEntry(standalone_cost=0.0, total_cost=0.0)

    return ArtifactCost({artifact_id: entry})
