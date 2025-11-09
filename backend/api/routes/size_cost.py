"""
Size-cost analysis endpoints.
"""
# pyright: reportMissingImports=false
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Path, status

import logger
from backend.models.size_cost import SizeCostRequest, SizeCostResponse
from backend.services.package_service import get_package_by_id
from metrics.size import calculate_size_score_cached

router = APIRouter(prefix="/size-cost", tags=["size-cost"])


@router.post("/", response_model=SizeCostResponse)
def check_size_cost(request: SizeCostRequest):
    """
    Check if a package meets size requirements for a given deployment target.

    Deployment targets:
    - raspberry_pi: Low-power edge device
    - jetson_nano: GPU-enabled edge device
    - desktop_pc: Standard desktop computer
    - aws_server: Cloud server with flexible resources

    Returns compatibility score (0-1) and whether it meets the threshold.
    """
    package = get_package_by_id(request.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{request.package_id}' not found"
        )

    # Get size score for the specified target
    size_scores = _get_size_scores(package)
    target = request.deployment_target.lower()

    if target not in size_scores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid deployment target '{target}'. Valid targets: {list(size_scores.keys())}"
        )

    score = size_scores[target]
    threshold = request.threshold if request.threshold is not None else 0.7
    meets_requirement = score >= threshold

    return SizeCostResponse(
        package_id=package.id,
        package_name=package.name,
        deployment_target=target,
        size_score=score,
        threshold=threshold,
        meets_requirement=meets_requirement,
        recommendation=_get_size_recommendation(score, target)
    )


@router.get("/{package_id:path}", response_model=dict)
def get_all_size_scores(package_id: str = Path(..., description="Package ID (can contain slashes)")):
    """
    Get size-cost scores for all deployment targets for a given package.
    """
    package = get_package_by_id(package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{package_id}' not found"
        )

    size_scores = _get_size_scores(package)

    return {
        "package_id": package.id,
        "package_name": package.name,
        "size_scores": size_scores,
        "recommendations": {
            target: _get_size_recommendation(score, target)
            for target, score in size_scores.items()
        }
    }


def _get_size_recommendation(score: float, target: str) -> str:
    """Generate a human-readable recommendation based on size score."""
    if score >= 0.9:
        return f"Excellent fit for {target}. Minimal resource usage."
    elif score >= 0.7:
        return f"Good fit for {target}. Reasonable resource usage."
    elif score >= 0.5:
        return f"Acceptable for {target}, but may have performance constraints."
    else:
        return f"Not recommended for {target}. Consider a smaller model or more powerful hardware."


def _get_size_scores(package: Any) -> Dict[str, float]:
    """
    Retrieve size scores from the metrics module with a fallback to stored data.
    """
    try:
        size_scores, _, _ = calculate_size_score_cached(package.URL)
        if isinstance(size_scores, dict) and size_scores:
            return size_scores
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug(f"Failed to calculate size scores via metrics for {package.id}: {exc}")

    stored_scores = getattr(package, "size_score", None)
    if isinstance(stored_scores, dict):
        return stored_scores

    return {}
