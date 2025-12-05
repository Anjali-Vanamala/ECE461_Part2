from __future__ import annotations

import asyncio
import re
import time
from typing import List
import requests

import regex
from fastapi import (APIRouter, BackgroundTasks, Body, HTTPException, Path,
                     Query, Response, status)

from backend.models import (Artifact, ArtifactCost, ArtifactCostEntry,
                            ArtifactData, ArtifactID, ArtifactMetadata,
                            ArtifactQuery, ArtifactRegistration, ArtifactType,
                            ModelRating, SimpleLicenseCheckRequest)
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


def process_model_artifact_async(
    url: str,
    artifact_id: str,
    name: str,
) -> None:
    """Background task to process model artifact asynchronously.

    Note: This function is synchronous but runs in a background thread
    to avoid blocking the event loop.
    """
    try:
        # Compute the artifact (this is the long-running operation)
        artifact, rating, dataset_name, dataset_url, code_name, code_url = compute_model_artifact(
            url,
            artifact_id=artifact_id,
            name_override=name,
        )

        # Save the completed artifact
        memory.save_artifact(
            artifact,
            rating=rating,
            dataset_name=dataset_name,
            dataset_url=dataset_url,
            code_name=code_name,
            code_url=code_url,
            processing_status="completed",
        )
        # Explicitly ensure processing status is set to completed
        memory.update_processing_status(artifact_id, "completed")
        if rating:
            memory.save_model_rating(artifact.metadata.id, rating)
    except Exception as e:
        # Mark as failed
        memory.update_processing_status(artifact_id, "failed")
        # Log the error but don't raise - the artifact is already registered
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to process model artifact {artifact_id}: {e}")


@router.post(
    "/artifact/{artifact_type}",
    response_model=Artifact,
    summary="Register a new artifact. (BASELINE)",
)
async def register_artifact(
    payload: ArtifactRegistration,
    background_tasks: BackgroundTasks,
    response: Response,
    artifact_type: ArtifactType = Path(..., description="Type of artifact being ingested."),
) -> Artifact:
    if memory.artifact_exists(artifact_type, payload.url):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Artifact exists already")

    if artifact_type == ArtifactType.MODEL:
        # Generate ID and create artifact immediately
        artifact_id = memory.generate_artifact_id()
        name = payload.name or _derive_name(payload.url)

        artifact = Artifact(
            metadata=ArtifactMetadata(
                name=name,
                id=artifact_id,
                type=artifact_type,
            ),
            data=ArtifactData(url=payload.url),
        )

        # Save artifact with "processing" status
        memory.save_artifact(artifact, processing_status="processing")

        # Process in background
        background_tasks.add_task(
            process_model_artifact_async,
            payload.url,
            artifact_id,
            name,
        )

        # Return 202 for models (async processing)
        response.status_code = status.HTTP_202_ACCEPTED
        return artifact

    # Dataset/Code artifacts are processed immediately
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

    # Return 201 for non-model artifacts (immediate processing)
    response.status_code = status.HTTP_201_CREATED
    return artifact


@router.get(
    "/artifacts/{artifact_type}/{artifact_id:path}",
    response_model=Artifact,
    summary="Interact with the artifact with this id. (BASELINE)",
    responses={
        400: {"description": "Malformed artifact_type or artifact_id."},
        404: {"description": "Artifact does not exist."},
        200: {"description": "Artifact retrieved successfully."},
        504: {"description": "Processing timeout."},
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

    # If model is still processing, wait (with timeout)
    if artifact_type_enum == ArtifactType.MODEL:
        import time
        max_wait = 120  # 2 minutes max wait
        poll_interval = 0.5  # Check every 500ms
        start_time = time.time()

        while True:
            processing_status = memory.get_processing_status(artifact_id)
            if processing_status == "completed":
                # Refresh artifact to get latest data
                artifact = memory.get_artifact(artifact_type_enum, artifact_id)
                break
            elif processing_status == "failed":
                raise HTTPException(
                    status_code=status.HTTP_424_FAILED_DEPENDENCY,
                    detail="Model processing failed.",
                )
            elif processing_status == "processing" or processing_status is None:
                # None means artifact not yet initialized - treat as processing
                if time.time() - start_time > max_wait:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Model processing timeout.",
                    )
                await asyncio.sleep(poll_interval)
            else:
                # Unknown status, assume completed
                break

    return artifact


@router.put(
    "/artifacts/{artifact_type}/{artifact_id}",
    response_model=Artifact,
    summary="Update this content of the artifact. (BASELINE)",
)
async def update_artifact(
    payload: Artifact,
    background_tasks: BackgroundTasks,
    response: Response,
    artifact_type: ArtifactType = Path(..., description="Type of artifact to update"),
    artifact_id: ArtifactID = Path(..., description="artifact id"),
) -> Artifact:
    if payload.metadata.id != artifact_id or payload.metadata.type != artifact_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not match path parameters",
        )

    if artifact_type == ArtifactType.MODEL:
        # Update model asynchronously (same pattern as POST)
        memory.save_artifact(payload, processing_status="processing")

        background_tasks.add_task(
            process_model_artifact_async,
            payload.data.url,
            artifact_id,
            payload.metadata.name,
        )

        response.status_code = status.HTTP_202_ACCEPTED
        return payload

    # Non-model artifacts are updated immediately
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
    # Wait for processing to complete if still processing
    import time
    max_wait = 120  # 2 minutes max wait
    poll_interval = 0.5  # Check every 500ms
    start_time = time.time()

    while True:
        processing_status = memory.get_processing_status(artifact_id)
        if processing_status == "completed":
            break
        elif processing_status == "failed":
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail="Model processing failed.",
            )
        elif processing_status == "processing" or processing_status is None:
            # None means artifact not yet initialized - treat as processing
            if time.time() - start_time > max_wait:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Model processing timeout.",
                )
            await asyncio.sleep(poll_interval)
        else:
            # Unknown status, try to get rating anyway
            break

    rating = memory.get_model_rating(artifact_id)
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist or lacks a rating.")
    return rating


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



COMPATIBLE_LICENSES = {
    "apache-2.0", "apache 2.0", "apache license 2.0", "apache",
    "mit", "mit license",
    "bsd-3-clause", "bsd-3", "bsd 3-clause", "bsd",
    "bsl-1.0", "boost software license",
    "lgpl-2.1", "lgpl 2.1", "lgplv2.1"   # only LGPL 2.1 allowed
}

INCOMPATIBLE_LICENSES = {
    "gpl", "gpl-2", "gpl-3", "gplv2", "gplv3", "gnu general public license",
    "agpl", "agpl-3", "affero gpl",
    "lgpl", "lgpl-3", "lgplv3",   # anything except LGPL 2.1
    "non-commercial", "non commercial", "commercial", "proprietary",
    "creative commons", "cc-by", "cc-by-nc"
}

def normalize_license(name: str) -> str:
    """
    Normalize a license string so it can be compared reliably.
    Handles: case, hyphens, underscores, punctuation, repeated spaces.
    """
    if not name:
        return "unknown"

    name = name.lower()

    # Replace punctuation with spaces
    name = re.sub(r"[_\-/,]+", " ", name)

    # Remove parentheses + version qualifiers
    name = re.sub(r"\(.*?\)", "", name)

    # Remove extra spaces
    name = " ".join(name.split())

    return name


def is_license_compatible(model_license: str, github_license: str) -> bool:
    """
    Return True if the model artifact license is compatible with the GitHub repo license.

    Compatibility rules:
      - Both must be in COMPATIBLE_LICENSES after normalization.
      - Anything in INCOMPATIBLE_LICENSES → immediately false.
      - Unknown → false.
    """
    model_norm = normalize_license(model_license)
    repo_norm = normalize_license(github_license)

    # Unknown license → incompatible
    if model_norm == "unknown":
        return False
    
    if repo_norm == "unknown":
        return False

    # Explicit incompatibility check
    if model_norm in INCOMPATIBLE_LICENSES or repo_norm in INCOMPATIBLE_LICENSES:
        return False

    # Both must be compatible
    if model_norm in COMPATIBLE_LICENSES and repo_norm in COMPATIBLE_LICENSES:
        return True

    # Otherwise incompatible
    return False


@router.post(
    "/artifact/model/{artifact_id}/license-check",
    summary="Assess license compatibility between model artifact and GitHub repo. (BASELINE)",
)
async def license_check(
    artifact_id: ArtifactID,
    payload: SimpleLicenseCheckRequest,
):
    # 1. Check artifact exists
    artifact = memory.get_artifact(ArtifactType.MODEL, artifact_id)
    if not artifact:
        raise HTTPException(404, "Artifact does not exist.")

    # 2. Extract model license
    model_license = memory.get_model_license(artifact_id)
    if not model_license:
        return False  # unknown → incompatible

    # 3. Parse GitHub URL
    match = re.search(r"github\.com/([^/]+)/([^/]+)", payload.github_url)
    if not match:
        raise HTTPException(400, "Malformed GitHub repository URL.")
    owner, repo = match.groups()

    # 4. Fetch GitHub license
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/license",
            timeout=10
        )
    except:
        raise HTTPException(502, "External license information could not be retrieved.")

    if resp.status_code == 404:
        raise HTTPException(404, "GitHub repository not found.")

    data = resp.json()
    github_license = data.get("license", {}).get("spdx_id")

    # 5. Compute compatibility
    compatible = is_license_compatible(model_license, github_license)

    return compatible
