from __future__ import annotations

import asyncio
import os
import re
import tempfile
import time
from typing import List
from urllib.parse import urlparse

import regex
import httpx
import requests
from fastapi import (APIRouter, BackgroundTasks, Body, HTTPException, Path,
                     Query, Request, Response, status)
from fastapi.responses import RedirectResponse, StreamingResponse
from huggingface_hub import HfApi, hf_hub_url

from backend.models import (Artifact, ArtifactCost, ArtifactCostEntry,
                            ArtifactData, ArtifactID, ArtifactMetadata,
                            ArtifactQuery, ArtifactRegistration, ArtifactType,
                            ModelRating, SimpleLicenseCheckRequest)
from backend.services.rating_service import compute_model_artifact
from backend.storage import memory, s3

router = APIRouter(tags=["artifacts"])


def _derive_name(url: str) -> str:
    stripped = url.strip().rstrip("/")
    if not stripped:
        return "artifact"
    return stripped.split("/")[-1]


def _get_base_url(request: Request | None = None) -> str:
    """
    Get base URL from request, with fallback to BASE_URL environment variable.
    Handles proxy headers (X-Forwarded-Host/Proto) for correct public URLs.
    """
    # 1. Check environment variable first (best for production/AWS)
    env_base = os.getenv("BASE_URL")
    if env_base:
        return env_base.rstrip('/')

    # 2. Try to construct from request
    if request:
        # Check standard proxy headers (ALB, API Gateway)
        forwarded_host = request.headers.get("X-Forwarded-Host")
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")

        if forwarded_host:
            # Reconstruct public URL from headers
            return f"{forwarded_proto}://{forwarded_host}".rstrip('/')

        # Fallback to direct request URL (local dev or direct access)
        return str(request.base_url).rstrip('/')

    # 3. Last resort default
    return "http://localhost:8000"


def _extract_model_id_from_url(url: str) -> str:
    """
    Extract HuggingFace model/dataset ID from URL.

    Handles formats like:
    - https://huggingface.co/namespace/model-name
    - https://huggingface.co/namespace/model-name/tree/main
    - https://huggingface.co/datasets/namespace/dataset-name
    """
    if 'huggingface.co' in url:
        pattern = r'huggingface\.co/(?:datasets/)?([^/]+/[^/?]+)'
        match = re.search(pattern, url)
        if match:
            model_id = match.group(1)
            # Remove /tree/main or similar suffixes
            if '/tree' in model_id:
                model_id = model_id.split('/tree')[0]
            return model_id

    # If it looks like 'namespace/model_name' without URL
    if '/' in url and ' ' not in url and '://' not in url:
        return url

    return url


def _get_huggingface_download_url(model_id: str, is_dataset: bool = False) -> str:
    """
    Get actual download URL for HuggingFace model/dataset.

    Uses huggingface_hub to get the primary model file URL.
    Falls back to constructing a /resolve/main/ URL for common model files.
    """
    try:
        api = HfApi()
        repo_type = "dataset" if is_dataset else "model"

        # Try to get model info to find the main model file
        try:
            if is_dataset:
                # For datasets, use dataset_info
                _ = api.dataset_info(repo_id=model_id)  # Check if dataset exists
            else:
                # For models, use model_info
                _ = api.model_info(repo_id=model_id)  # Check if model exists

            # Look for common model file patterns
            model_files = [
                "model.safetensors",
                "pytorch_model.bin",
                "model.bin",
                "tf_model.h5",
            ]

            # Check if any model files exist
            for file_name in model_files:
                try:
                    # Use hf_hub_url to get the download URL
                    download_url = hf_hub_url(
                        repo_id=model_id,
                        filename=file_name,
                        repo_type=repo_type,
                        revision="main"
                    )
                    # Verify the file exists by checking if URL is accessible
                    test_response = requests.head(download_url, timeout=5, allow_redirects=True)
                    if test_response.status_code == 200:
                        return download_url
                except Exception:
                    continue

            # If no model file found, return a zip archive URL
            # HuggingFace doesn't provide direct zip URLs, so we'll use the resolve URL for README
            # and let the client handle it, or construct a repo snapshot URL
            return f"https://huggingface.co/{model_id}/resolve/main/README.md"

        except Exception:
            # Fallback: construct resolve URL for common files
            for file_name in ["model.safetensors", "pytorch_model.bin", "model.bin"]:
                fallback_url = f"https://huggingface.co/{model_id}/resolve/main/{file_name}"
                try:
                    test_response = requests.head(fallback_url, timeout=5, allow_redirects=True)
                    if test_response.status_code == 200:
                        return fallback_url
                except Exception:
                    continue

            # Last resort: return README URL
            return f"https://huggingface.co/{model_id}/resolve/main/README.md"

    except Exception:
        # Final fallback: return a constructed URL
        return f"https://huggingface.co/{model_id}/resolve/main/README.md"


def _get_github_download_url(repo_url: str) -> str:
    """
    Get zip download URL for GitHub repository.

    Extracts owner/repo from GitHub URL and constructs archive download URL.
    Defaults to main branch (most modern repos use this).
    """
    parsed = urlparse(repo_url)
    path = parsed.path.strip('/')
    parts = path.split('/')

    # GitHub URLs: github.com/owner/repo or github.com/owner/repo/tree/branch
    if len(parts) >= 2:
        owner = parts[0]
        repo = parts[1]

        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]

        # Detect branch from URL if present, otherwise default to main
        branch = "main"
        if len(parts) >= 4 and parts[2] == "tree":
            branch = parts[3]

        return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    # Fallback: return original URL
    return repo_url


def _get_source_download_url(artifact: Artifact) -> str:
    """
    Get actual download URL based on artifact type and source.

    Routes to appropriate helper based on URL pattern.
    Returns downloadable file URL.
    Validates the URL before returning.
    """
    source_url = artifact.data.url

    # Validate source URL is not empty
    if not source_url or not source_url.strip():
        raise ValueError("Source URL is empty")

    download_url = None

    # Check if it's a HuggingFace URL
    if 'huggingface.co' in source_url:
        is_dataset = '/datasets/' in source_url or artifact.metadata.type == ArtifactType.DATASET
        model_id = _extract_model_id_from_url(source_url)
        download_url = _get_huggingface_download_url(model_id, is_dataset=is_dataset)

    # Check if it's a GitHub URL
    elif 'github.com' in source_url:
        download_url = _get_github_download_url(source_url)

    # For other URLs, return as-is (assume it's already a direct download URL)
    else:
        download_url = source_url

    # Validate URL format
    try:
        parsed = urlparse(download_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {download_url}")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    return download_url


def _get_download_filename(artifact: Artifact, source_url: str) -> str:
    """
    Determine filename for download based on artifact and source URL.
    Sanitizes filename to be safe for HTTP headers.
    """
    artifact_name = artifact.metadata.name or "artifact"

    # Sanitize artifact name (remove/replace unsafe characters)
    # Remove quotes, backslashes, and other problematic chars
    safe_name = artifact_name.replace('"', '').replace('\\', '').replace('\n', '').replace('\r', '')
    # Replace spaces and other special chars with underscores
    safe_name = re.sub(r'[^\w\-_\.]', '_', safe_name)
    # Ensure name is not empty after sanitization
    if not safe_name or safe_name.strip() == '':
        safe_name = "artifact"
    # Limit length to avoid header issues
    if len(safe_name) > 200:
        safe_name = safe_name[:200]

    # Try to extract extension from source URL
    if '.zip' in source_url:
        extension = '.zip'
    elif '.safetensors' in source_url:
        extension = '.safetensors'
    elif '.bin' in source_url:
        extension = '.bin'
    elif '.h5' in source_url:
        extension = '.h5'
    else:
        # Default based on artifact type
        if artifact.metadata.type == ArtifactType.CODE:
            extension = '.zip'
        else:
            extension = '.bin'

    return f"{safe_name}{extension}"


def calibrate_regex_timeout(test_text) -> float:
    """
    Measures how long regex takes in this platform for a safe case.
    The timeout is set to allow legitimate patterns while blocking catastrophic ones.
    """
    test_pattern = r"a+"
    test2_pattern = r"ece461"

    start = time.perf_counter()
    regex.search(test_pattern, test_text)
    baseline = time.perf_counter() - start

    start = time.perf_counter()
    regex.search(test2_pattern, test_text)
    baseline2 = time.perf_counter() - start

    # Use a more lenient multiplier to avoid false positives on valid patterns
    # Minimum 0.01 seconds to handle legitimate complex patterns
    return max(0.01, baseline * 2, baseline2 * 2)


def safe_regex_search(pattern: str, text: str, timeout: float = 0.1) -> bool | None:
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
    test_string = "a" * 5000
    timeout_1 = calibrate_regex_timeout(test_string)
    initial_test = safe_regex_search(regex_str, "a" * 5000, timeout_1)
    if initial_test is None:
        raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")

    for store in memory._TYPE_TO_STORE.values():
        for record in store.values():  # type: ignore[attr-defined]
            name = record.artifact.metadata.name
            test_readme = None
            if record.artifact.metadata.type == ArtifactType.MODEL:
                readme = memory.get_model_readme(record.artifact.metadata.id)
            else:
                readme = "temp"
            if readme is not None and len(readme) > 10:
                timeout = calibrate_regex_timeout(readme)
                test_readme = safe_regex_search(regex_str, readme, timeout)
            else:
                timeout = timeout_1
            test = safe_regex_search(regex_str, name, timeout)
            if test is None and test_readme is None:
                raise HTTPException(400, "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid")
            if test or test_readme:
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


def validate_model_rating(rating: ModelRating) -> bool:
    """
    Returns True if ALL subratings are >= 0.5, otherwise False.

    Works generically across nested rating fields, including:
        - performance_claims
        - size_score.*
        - dataset_quality
        - code_quality
        - dataset_and_code_score
        - ramp_up_time
        - bus_factor
        - etc.
    """

    def check(obj):
        for attr, value in obj.__dict__.items():
            if isinstance(value, (int, float)):
                if value < 0.5:
                    return False
            elif hasattr(value, "__dict__"):
                if not check(value):
                    return False
        return True

    return check(rating)


def validate_net_score(rating: ModelRating) -> bool:
    """
    Returns True if net_score >= 0.5, otherwise False.
    """
    return getattr(rating, "net_score", 0.0) >= 0.5


async def process_model_artifact_async(
    url: str,
    artifact_id: str,
    name: str,
) -> None:
    import logging
    logger = logging.getLogger(__name__)
    temp_file_path = None

    try:
        # Compute the artifact (long-running)
        artifact, rating, dataset_name, dataset_url, code_name, code_url, license, readme = compute_model_artifact(
            url,
            artifact_id=artifact_id,
            name_override=name,
        )
        strict_check = False
        soft_check = False
        # 🔍 NEW: Validate rating before saving it
        if rating and not validate_model_rating(rating) and strict_check:
            # Mark as failed and DO NOT save final artifact or rating
            memory.update_processing_status(artifact_id, "failed")

            # Optionally discard partial model entirely:
            memory.delete_artifact(ArtifactType.MODEL, artifact_id)

            logger.error(
                f"Model {artifact_id} rejected: one or more subratings below 0.5."
            )
            return  # stops processing here
        if rating and not validate_net_score(rating) and soft_check:
            # Mark as failed and DO NOT save final artifact or rating
            memory.update_processing_status(artifact_id, "failed")

            # Optionally discard partial model entirely:
            memory.delete_artifact(ArtifactType.MODEL, artifact_id)

            logger.error(
                f"Model {artifact_id} rejected: one or more subratings below 0.5."
            )
            return  # stops processing here

        # CRITICAL: Mark artifact as completed FIRST (before S3 operations)
        # This ensures get_artifact() doesn't timeout waiting for S3 uploads
        memory.save_artifact(
            artifact,
            rating=rating,
            license=license,
            dataset_name=dataset_name,
            dataset_url=dataset_url,
            code_name=code_name,
            code_url=code_url,
            readme=readme,
            processing_status="completed",
        )

        memory.update_processing_status(artifact_id, "completed")

        if rating:
            memory.save_model_rating(artifact.metadata.id, rating)

        # NOW: Download and store artifact file in S3 (non-blocking, happens after completion)
        # This won't block get_artifact() from succeeding
        try:
            # Get source download URL
            source_download_url = _get_source_download_url(artifact)

            # Download file to temporary location
            logger.info(f"Downloading artifact {artifact_id} from {source_download_url} for S3 storage")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
            temp_file_path = temp_file.name
            temp_file.close()

            # Download with streaming to handle large files (async)
            async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
                async with client.stream('GET', source_download_url) as download_response:
                    download_response.raise_for_status()

                    # Write to temp file in chunks
                    with open(temp_file_path, 'wb') as f:
                        async for chunk in download_response.aiter_bytes(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

            logger.info(f"Downloaded artifact {artifact_id} to temp file, size: {os.path.getsize(temp_file_path)} bytes")

            # Upload to S3 using helper function
            upload_success = s3.upload_file_to_s3(
                temp_file_path,
                artifact_type="model",
                artifact_id=artifact_id,
            )

            if not upload_success:
                logger.warning(f"S3 upload failed for artifact {artifact_id}, but artifact is already marked completed")
            else:
                logger.info(f"Successfully uploaded artifact {artifact_id} to S3")
        except ValueError as e:
            # S3 bucket not configured - log warning but continue
            logger.warning(f"S3 not configured: {e}, skipping file storage for {artifact_id}")
        except RuntimeError as e:
            # boto3 not available - log warning but continue
            logger.warning(f"boto3 not available: {e}, skipping S3 storage for {artifact_id}")
        except Exception as download_error:
            logger.error(f"File download/upload failed for artifact {artifact_id}: {download_error}, but artifact is already marked completed")
            # Artifact is already marked completed, so this is non-critical

    except Exception as e:
        memory.update_processing_status(artifact_id, "failed")
        logger.error(f"Failed to process model artifact {artifact_id}: {e}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {cleanup_error}")


@router.post(
    "/artifact/{artifact_type}",
    response_model=Artifact,
    summary="Register a new artifact. (BASELINE)",
)
async def register_artifact(
    request: Request,
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

        # Construct download_url dynamically
        base_url = _get_base_url(request)
        download_url = f"{base_url}/artifacts/{artifact_type.value}/{artifact_id}/download"

        artifact = Artifact(
            metadata=ArtifactMetadata(
                name=name,
                id=artifact_id,
                type=artifact_type,
            ),
            data=ArtifactData(url=payload.url, download_url=download_url),
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

    # Construct download_url dynamically
    base_url = _get_base_url(request)
    download_url = f"{base_url}/artifacts/{artifact_type.value}/{artifact_id}/download"

    artifact = Artifact(
        metadata=ArtifactMetadata(
            name=artifact_name,
            id=artifact_id,
            type=artifact_type,
        ),
        data=ArtifactData(url=payload.url, download_url=download_url),
    )
    memory.save_artifact(artifact)

    # Return 201 for non-model artifacts (immediate processing)
    response.status_code = status.HTTP_201_CREATED
    return artifact


@router.get(
    "/artifacts/{artifact_type}/{artifact_id}/download",
    summary="Download artifact bundle. (BASELINE)",
    responses={
        200: {"description": "Stream artifact file"},
        202: {"description": "Artifact still processing"},
        404: {"description": "Artifact does not exist"},
        424: {"description": "Artifact processing failed"},
        502: {"description": "Source download failed"},
        504: {"description": "Download timeout"},
    },
)
async def download_artifact(
    request: Request,
    artifact_type: ArtifactType = Path(..., description="Type of artifact to download"),
    artifact_id: ArtifactID = Path(..., description="Artifact id"),
):
    """
    Download endpoint for artifacts.

    Returns a pre-signed S3 URL redirect for artifacts stored in S3.
    For model artifacts that are still processing, returns 202 Accepted.
    """
    import logging
    logger = logging.getLogger(__name__)

    # FastAPI already validates artifact_type (ArtifactType enum) and artifact_id (ArtifactID pattern)
    # via type annotations, so we can use them directly

    # 1. Check if artifact exists
    artifact = memory.get_artifact(artifact_type, artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=404,
            detail="404: Artifact does not exist.",
        )

    # 2. For models, check processing status
    if artifact_type == ArtifactType.MODEL:
        processing_status = memory.get_processing_status(artifact_id)

        if processing_status == "processing":
            # Artifact is still being processed - return 202 Accepted
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Artifact is still processing.",
            )

        if processing_status == "failed":
            # Artifact processing failed - return 424 Failed Dependency
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail="Artifact processing failed.",
            )

    # 3. Check if file exists in S3
    try:
        file_exists = s3.file_exists_in_s3(artifact_type.value, artifact_id)
        
        if not file_exists:
            # File not in S3 - fallback to proxy download
            logger.info(f"File not found in S3 for artifact {artifact_id}, falling back to proxy download")
            return await _proxy_download_fallback(artifact, artifact_type)
        
        # File exists - generate pre-signed S3 URL
        presigned_url = s3.generate_presigned_download_url(
            artifact_type.value,
            artifact_id,
            expiration=900  # 15 minutes
        )

        if not presigned_url:
            # Failed to generate URL - fallback to proxy
            logger.warning(f"Failed to generate pre-signed URL for artifact {artifact_id}, falling back to proxy")
            return await _proxy_download_fallback(artifact, artifact_type)

        # Redirect to pre-signed S3 URL
        return RedirectResponse(url=presigned_url, status_code=status.HTTP_302_FOUND)

    except ValueError:
        # S3 bucket not configured - fallback to proxy
        logger.warning(f"S3 bucket not configured, falling back to proxy download for artifact {artifact_id}")
        return await _proxy_download_fallback(artifact, artifact_type)
    except RuntimeError:
        # boto3 not available - fallback to proxy
        logger.warning(f"boto3 not available, falling back to proxy download for artifact {artifact_id}")
        return await _proxy_download_fallback(artifact, artifact_type)
    except Exception as e:
        # Other S3 error - fallback to proxy
        logger.error(f"S3 error for artifact {artifact_id}: {e}, falling back to proxy download")
        return await _proxy_download_fallback(artifact, artifact_type)


async def _proxy_download_fallback(
    artifact: Artifact,
    artifact_type: ArtifactType,
) -> StreamingResponse:
    """
    Fallback function to proxy download from source if file not in S3.
    This handles cases where S3 upload may have failed during ingestion.
    """
    # Get source download URL
    try:
        source_download_url = _get_source_download_url(artifact)
    except (ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to determine source download URL.",
        )

    # Fetch from source with streaming (async)
    DOWNLOAD_TIMEOUT = 300.0  # 5 minutes
    filename = _get_download_filename(artifact, source_download_url)
    content_type = 'application/octet-stream'  # Default

    async def stream_response():
        """Async generator to stream the response"""
        try:
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
                async with client.stream('GET', source_download_url) as source_response:
                    # Check status code before streaming
                    if source_response.status_code == 404:
                        # Return empty stream - error will be handled by status check
                        return
                    
                    source_response.raise_for_status()
                    
                    # Stream chunks to client
                    async for chunk in source_response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            yield chunk
        except httpx.TimeoutException:
            # Can't raise HTTPException in generator, but we can stop streaming
            return
        except httpx.ConnectError:
            return
        except httpx.HTTPStatusError:
            return
        except Exception:
            return

    # Validate the request BEFORE creating StreamingResponse
    # This allows us to raise HTTPException before streaming starts
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Make a quick HEAD request to validate and get headers
            try:
                head_response = await client.head(source_download_url)
                if head_response.status_code == 200:
                    content_type = head_response.headers.get('Content-Type', content_type)
                elif head_response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Source file not found.",
                    )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Download timeout from source.",
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Cannot connect to source server.",
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Source file not found.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Source download failed.",
                )
            except HTTPException:
                # Re-raise HTTPExceptions
                raise
            except Exception:
                # For other errors, try to proceed with streaming
                # (some servers don't support HEAD)
                pass
    except HTTPException:
        # Re-raise HTTPExceptions from validation
        raise
    except Exception:
        # If validation fails but it's not an HTTPException, continue
        # (some servers don't support HEAD requests)
        pass

    # Build headers
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
    }

    # Return streaming response with async generator
    return StreamingResponse(
        stream_response(),
        media_type=content_type,
        headers=headers
    )


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
    request: Request,
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
            elif processing_status is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model doesn't exist.",
                )
            elif processing_status == "processing":
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

    # Populate download_url if missing (for backward compatibility)
    # artifact is guaranteed to be non-None here due to check above
    assert artifact is not None, "Artifact should not be None at this point"
    if not artifact.data.download_url:
        base_url = _get_base_url(request)
        artifact_type_str = artifact_type.lower() if isinstance(artifact_type, str) else artifact_type.value
        artifact.data.download_url = f"{base_url}/artifacts/{artifact_type_str}/{artifact_id}/download"

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
        elif processing_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model doesn't exist.",
            )
        elif processing_status == "processing":
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
    except Exception:
        raise HTTPException(502, "External license information could not be retrieved.")

    if resp.status_code == 404:
        raise HTTPException(404, "GitHub repository not found.")

    data = resp.json()
    github_license = data.get("license", {}).get("spdx_id")

    # 5. Compute compatibility
    compatible = is_license_compatible(model_license, github_license)

    return compatible
