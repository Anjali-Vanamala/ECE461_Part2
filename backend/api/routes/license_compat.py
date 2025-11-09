"""
License compatibility check endpoints.
"""
# pyright: reportMissingImports=false
from typing import Any, Tuple

from fastapi import APIRouter, HTTPException, Path, status

import logger
from backend.models.license_compat import (
    LicenseCompatRequest,
    LicenseCompatResponse,
)
from backend.services.package_service import get_package_by_id
from metrics.license import (
    download_readme_directly,
    extract_license_section,
    extract_model_id_from_url,
    get_license_score_cached,
)

router = APIRouter(prefix="/license-compatibility", tags=["license-compatibility"])

# Known license compatibility matrix
# 1.0 = fully compatible, 0.5 = conditionally compatible, 0.0 = incompatible
LICENSE_COMPATIBILITY = {
    "MIT": {
        "MIT": 1.0,
        "Apache-2.0": 1.0,
        "BSD": 1.0,
        "GPL": 0.5,  # GPL is more restrictive
        "LGPL": 0.5,
        "proprietary": 0.5
    },
    "Apache-2.0": {
        "MIT": 1.0,
        "Apache-2.0": 1.0,
        "BSD": 1.0,
        "GPL": 0.5,
        "LGPL": 0.5,
        "proprietary": 0.5
    },
    "BSD": {
        "MIT": 1.0,
        "Apache-2.0": 1.0,
        "BSD": 1.0,
        "GPL": 0.5,
        "LGPL": 0.5,
        "proprietary": 0.5
    },
    "GPL": {
        "MIT": 1.0,
        "Apache-2.0": 1.0,
        "BSD": 1.0,
        "GPL": 1.0,
        "LGPL": 1.0,
        "proprietary": 0.0  # GPL incompatible with proprietary
    },
    "LGPL": {
        "MIT": 1.0,
        "Apache-2.0": 1.0,
        "BSD": 1.0,
        "GPL": 1.0,
        "LGPL": 1.0,
        "proprietary": 0.5
    },
    "unknown": {
        "MIT": 0.0,
        "Apache-2.0": 0.0,
        "BSD": 0.0,
        "GPL": 0.0,
        "LGPL": 0.0,
        "proprietary": 0.0
    }
}


@router.post("/", response_model=LicenseCompatResponse)
def check_license_compatibility(request: LicenseCompatRequest):
    """
    Check if a package's license is compatible with a target license.

    Returns:
    - compatibility_score: 1.0 (fully compatible), 0.5 (conditionally compatible), 0.0 (incompatible)
    - is_compatible: True if score >= threshold (default 0.5)
    - recommendation: Human-readable explanation
    """
    package = get_package_by_id(request.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{request.package_id}' not found"
        )

    # Determine package license (from license score)
    # In Phase 1, license score of 0.0 means no/unknown license, 1.0 means has license
    license_score, license_latency, package_license = _get_license_details(package)
    logger.debug(
        f"License metrics for {package.id}: score={license_score}, latency={license_latency}ms, inferred={package_license}"
    )

    target_license = request.target_license
    threshold = request.threshold if request.threshold is not None else 0.5

    # Check compatibility
    compat_matrix = LICENSE_COMPATIBILITY.get(package_license, LICENSE_COMPATIBILITY["unknown"])
    compatibility_score = compat_matrix.get(target_license, 0.0)
    is_compatible = compatibility_score >= threshold

    return LicenseCompatResponse(
        package_id=package.id,
        package_name=package.name,
        package_license=package_license,
        target_license=target_license,
        compatibility_score=compatibility_score,
        threshold=threshold,
        is_compatible=is_compatible,
        recommendation=_get_license_recommendation(
            package_license, target_license, compatibility_score
        )
    )


@router.get("/{package_id:path}", response_model=dict)
def get_license_info(package_id: str = Path(..., description="Package ID (can contain slashes)")):
    """
    Get license information for a package.
    """
    package = get_package_by_id(package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{package_id}' not found"
        )

    license_score, license_latency, package_license = _get_license_details(package)
    package_has_license = license_score > 0.0

    return {
        "package_id": package.id,
        "package_name": package.name,
        "license_score": round(license_score, 2),
        "license_latency": license_latency,
        "inferred_license": package_license,
        "has_license": package_has_license,
        "compatibility_matrix": LICENSE_COMPATIBILITY.get(package_license, {})
    }


def _get_license_details(package: Any) -> Tuple[float, int, str]:
    """
    Retrieve license score and inferred license type via the metrics module.
    """
    score = getattr(package, "license", 0.0)
    latency = 0
    license_text = ""

    try:
        score, latency = get_license_score_cached(package.URL)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug(f"Failed to compute license score via metrics for {package.id}: {exc}")

    try:
        model_id = extract_model_id_from_url(package.URL)
        readme = download_readme_directly(model_id)
        license_text = extract_license_section(readme)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug(f"Failed to extract license section for {package.id}: {exc}")

    inferred_license = _infer_license_from_text(license_text or "")

    # Preserve previous permissive assumption if metrics report a positive score but no explicit license found.
    if inferred_license == "unknown" and score > 0.0:
        inferred_license = "Apache-2.0"

    return score, latency, inferred_license


def _infer_license_from_text(license_text: str) -> str:
    """
    Infer license type from text extracted from the README.
    """
    text_lower = license_text.lower()

    if not text_lower.strip():
        return "unknown"

    if "lgpl" in text_lower:
        return "LGPL"
    if "gpl" in text_lower:
        return "GPL"
    if "mit" in text_lower:
        return "MIT"
    if "apache" in text_lower:
        return "Apache-2.0"
    if "bsd" in text_lower:
        return "BSD"
    if any(term in text_lower for term in ["proprietary", "non-commercial", "non commercial"]):
        return "proprietary"

    return "unknown"


def _get_license_recommendation(pkg_license: str, target_license: str, score: float) -> str:
    """Generate human-readable license compatibility recommendation."""
    if score >= 1.0:
        return f"Fully compatible. {pkg_license} can be used with {target_license} projects."
    elif score >= 0.5:
        return f"Conditionally compatible. {pkg_license} may be used with {target_license}, but review license terms carefully."
    else:
        return f"Incompatible. {pkg_license} cannot be legally combined with {target_license} projects."
