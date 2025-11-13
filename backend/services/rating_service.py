from __future__ import annotations

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests as rq
from huggingface_hub import HfApi, hf_hub_url

from backend.models import (Artifact, ArtifactData, ArtifactMetadata,
                            ArtifactType, ModelRating)
from backend.storage import memory
from metric_concurrent import main as run_metrics
from metrics.size import calculate_size_score


def _derive_name_from_url(url: str) -> str:
    stripped = url.strip().rstrip("/")
    if not stripped:
        return "artifact"
    return stripped.split("/")[-1]


def _fetch_model_info(raw_model_url: str) -> Tuple[dict, str]:
    parsed = urlparse(raw_model_url)
    model_path = parsed.path.strip("/")
    parts = model_path.split("/")
    if "tree" in parts:
        tree_index = parts.index("tree")
        model_path = "/".join(parts[:tree_index])

    model_info: dict = {}
    model_readme_text = ""

    # Use huggingface_hub library which handles auth automatically
    # If auth fails, we'll gracefully degrade (no dataset/code extraction)
    try:
        api = HfApi()
        model_info_obj = api.model_info(repo_id=model_path)
        # Convert to dict format expected by metrics
        model_info = {
            "id": model_info_obj.id,
            "modelId": getattr(model_info_obj, "modelId", None),
            "author": getattr(model_info_obj, "author", None),
            "sha": getattr(model_info_obj, "sha", None),
            "lastModified": str(getattr(model_info_obj, "lastModified", "")),
            "private": getattr(model_info_obj, "private", False),
            "disabled": getattr(model_info_obj, "disabled", False),
            "gated": getattr(model_info_obj, "gated", False),
            "pipeline_tag": getattr(model_info_obj, "pipeline_tag", None),
            "tags": getattr(model_info_obj, "tags", []),
            "downloads": getattr(model_info_obj, "downloads", 0),
            "likes": getattr(model_info_obj, "likes", 0),
            "library_name": getattr(model_info_obj, "library_name", None),
            "cardData": getattr(model_info_obj, "cardData", {}),
            "siblings": [{"rfilename": s.rfilename} for s in getattr(model_info_obj, "siblings", [])],
        }
        # Extract datasets from cardData if available
        card_data = getattr(model_info_obj, "cardData", {}) or {}
        if isinstance(card_data, dict) and "datasets" in card_data:
            model_info["datasets"] = card_data.get("datasets")

        # Also check tags for dataset references
        tags = getattr(model_info_obj, "tags", [])
        dataset_tags = [tag.replace("dataset:", "") for tag in tags if tag.startswith("dataset:")]
        if dataset_tags and "datasets" not in model_info:
            model_info["datasets"] = dataset_tags
    except Exception:
        model_info = {}

    # Fetch README using huggingface_hub
    try:
        readme_url = hf_hub_url(repo_id=model_path, filename="README.md", repo_type="model")
        readme_response = rq.get(readme_url, timeout=30)
        if readme_response.status_code == 200:
            model_readme_text = readme_response.text.lower()
    except Exception:
        model_readme_text = ""

    return model_info, model_readme_text


def _extract_dataset_name(model_info: dict, readme_text: str) -> Optional[str]:
    datasets = model_info.get("datasets")
    if isinstance(datasets, list) and datasets:
        candidate = datasets[0]
        if isinstance(candidate, str):
            return candidate.split("/")[-1]
    match = re.search(r"dataset[s]?:\s*([a-z0-9_\-]+)", readme_text)
    if match:
        return match.group(1)
    return None


def _extract_code_repo(model_info: dict, readme_text: str) -> Optional[str]:
    card_data = model_info.get("cardData") or {}
    code_repo = card_data.get("code_repository")
    if isinstance(code_repo, str) and code_repo:
        return code_repo
    match = re.search(r"https://github\.com/[\w\-]+/[\w\-]+", readme_text)
    if match:
        return match.group(0)
    return None


def _resolve_dataset(dataset_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not dataset_name:
        return None, None

    normalized = dataset_name.split("/")[-1].lower()
    record = memory.find_dataset_by_name(normalized)
    if record:
        return normalized, record.artifact.data.url

    # Fallback: assume HuggingFace dataset namespace
    return normalized, f"https://huggingface.co/datasets/{normalized}" if normalized else None


def _fetch_code_metadata(code_url: str) -> Tuple[dict, str]:
    code_info: dict = {}
    code_readme = ""

    match = re.search(r"github\.com/([^/]+)/([^/]+)", code_url)
    if not match:
        return code_info, code_readme

    owner, repo = match.groups()
    repo = repo.replace('.git', '')
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        response = rq.get(api_url, timeout=30)
        if response.status_code == 200:
            code_info = response.json()
    except Exception:
        code_info = {}

    try:
        readme_response = rq.get(
            f"{api_url}/readme",
            headers={'Accept': 'application/vnd.github.v3.raw'},
            timeout=30,
        )
        if readme_response.status_code == 200:
            code_readme = readme_response.text.lower()
    except Exception:
        code_readme = ""

    return code_info, code_readme


def _resolve_code(code_repo: Optional[str], code_name: Optional[str]) -> Tuple[Optional[str], Optional[str], dict, str]:
    resolved_name = code_name
    resolved_url = None
    code_info: dict = {}
    code_readme = ""

    if code_repo:
        resolved_url = code_repo
        resolved_name = _derive_name_from_url(code_repo).lower()
    if resolved_name:
        record = memory.find_code_by_name(resolved_name)
        if record:
            resolved_url = record.artifact.data.url

    if resolved_url:
        code_info, code_readme = _fetch_code_metadata(resolved_url)

    return resolved_name, resolved_url, code_info, code_readme


def compute_model_artifact(
    url: str,
    *,
    artifact_id: Optional[str] = None,
    name_override: Optional[str] = None,
) -> tuple[Artifact, ModelRating, Optional[str], Optional[str], Optional[str], Optional[str]]:
    name = name_override or _derive_name_from_url(url)
    artifact_id = artifact_id or memory.generate_artifact_id()

    # Fetch model info to extract dataset/code names from README
    # We'll use these names to link to already-registered artifacts
    model_info, readme_text = _fetch_model_info(url)

    # Extract dataset and code names from the model card
    dataset_name_hint = _extract_dataset_name(model_info, readme_text)
    code_repo_hint = _extract_code_repo(model_info, readme_text)
    code_name_hint = _derive_name_from_url(code_repo_hint).lower() if code_repo_hint else None

    # Now look up registered artifacts by these names
    dataset_url = None
    dataset_name = None
    if dataset_name_hint:
        dataset_record = memory.find_dataset_by_name(dataset_name_hint)
        if dataset_record:
            dataset_url = dataset_record.artifact.data.url
            dataset_name = dataset_record.artifact.metadata.name
        else:
            dataset_name = dataset_name_hint  # Store the name for future linking

    code_url = None
    code_name = None
    code_info = {}
    code_readme = ""
    if code_name_hint:
        code_record = memory.find_code_by_name(code_name_hint)
        if code_record:
            code_url = code_record.artifact.data.url
            code_name = code_record.artifact.metadata.name
        else:
            code_name = code_name_hint  # Store the name for future linking
            # Try using the hint URL directly if it's a valid GitHub URL
            if code_repo_hint and 'github.com' in code_repo_hint:
                code_url = code_repo_hint

    # Fetch code metadata if we have a URL
    if code_url:
        code_info, code_readme = _fetch_code_metadata(code_url)

    metrics = run_metrics(
        model_info,
        readme_text,
        url,
        code_info,
        code_readme,
        dataset_url or "",
        dataset_name=dataset_name,
        code_name=code_name,
    )

    if not isinstance(metrics, (list, tuple)) or len(metrics) != 11:
        raise ValueError("Metric computation failed")

    size_scores, net_size_score, _ = calculate_size_score(url)

    (
        net_size_score_metric,
        license_score,
        ramp_score,
        bus_score,
        dc_score,
        data_quality_score,
        code_quality_score,
        perf_score,
        repro_score,
        review_score,
        tree_score,
    ) = metrics

    net_score = round(
        sum([
            0.09 * license_score,
            0.10 * ramp_score,
            0.11 * net_size_score_metric,
            0.13 * data_quality_score,
            0.10 * bus_score,
            0.13 * dc_score,
            0.10 * code_quality_score,
            0.09 * perf_score,
            0.05 * repro_score,
            0.05 * review_score,
            0.05 * tree_score,
        ]),
        2,
    )

    rating = ModelRating(
        name=name,
        category="MODEL",
        net_score=net_score,
        net_score_latency=0.0,
        ramp_up_time=ramp_score,
        ramp_up_time_latency=0.0,
        bus_factor=bus_score,
        bus_factor_latency=0.0,
        performance_claims=perf_score,
        performance_claims_latency=0.0,
        license=license_score,
        license_latency=0.0,
        dataset_and_code_score=dc_score,
        dataset_and_code_score_latency=0.0,
        dataset_quality=data_quality_score,
        dataset_quality_latency=0.0,
        code_quality=code_quality_score,
        code_quality_latency=0.0,
        reproducibility=repro_score,
        reproducibility_latency=0.0,
        reviewedness=review_score,
        reviewedness_latency=0.0,
        tree_score=tree_score,
        tree_score_latency=0.0,
        size_score=size_scores,
        size_score_latency=0.0,
    )

    artifact = Artifact(
        metadata=ArtifactMetadata(
            name=name,
            id=artifact_id,
            type=ArtifactType.MODEL,
        ),
        data=ArtifactData(url=url),
    )

    return artifact, rating, dataset_name, dataset_url, code_name, code_url
