from __future__ import annotations

import re
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import requests as rq
from huggingface_hub import HfApi, hf_hub_url

import logger
from backend.models import (Artifact, ArtifactData, ArtifactMetadata,
                            ArtifactType, ModelRating, SizeScore)
from backend.storage import memory
from metric_concurrent import main as run_metrics
from metrics.size import calculate_size_score


def _derive_name_from_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return "artifact"

    # Special handling for GitHub: repo is always the *second* path component
    if "github.com" in url:
        parts = url.split("/")
        if len(parts) >= 5:
            return parts[4].replace(".git", "").lower()

    return url.split("/")[-1].lower()


def _fetch_model_info(raw_model_url: str) -> Tuple[dict, str]:
    parsed = urlparse(raw_model_url)
    model_path = parsed.path.strip("/")
    parts = model_path.split("/")

    # Remove "tree/main" or similar
    if "tree" in parts:
        model_path = "/".join(parts[: parts.index("tree")])

    hfhub_info = {}
    rest_info = {}
    model_readme_text = ""

    # -------------------------------------------------------
    # 1. Get model info from huggingface_hub (fast + reliable)
    # -------------------------------------------------------
    try:
        api = HfApi()
        info = api.model_info(repo_id=model_path)
        hfhub_info = info.__dict__
    except Exception:
        hfhub_info = {}

    # -------------------------------------------------------
    # 2. Get REST API model info (this has spaces, author, modelId)
    # -------------------------------------------------------
    try:
        rest_url = f"https://huggingface.co/api/models/{model_path}"
        rest_response = rq.get(rest_url, timeout=15)
        if rest_response.status_code == 200:
            rest_info = rest_response.json()
    except Exception:
        rest_info = {}

    # -------------------------------------------------------
    # 3. Merge HFHub + REST into unified model_info
    # -------------------------------------------------------
    model_info = {}
    # Always include ID
    model_info["id"] = hfhub_info.get("id", rest_info.get("id", model_path))
    model_info["modelId"] = rest_info.get("modelId", model_info["id"])

    # Author (REST is more reliable)
    model_info["author"] = rest_info.get(
        "author",
        hfhub_info.get("author", None)
    )

    # Last Modified — normalize to ISO string
    lm = (
        rest_info.get("lastModified") or hfhub_info.get("lastModified")
    )
    if hasattr(lm, "isoformat"):
        lm = lm.isoformat()  # type: ignore[union-attr]
    model_info["lastModified"] = lm or None

    # Tags (HFHub reliable)
    model_info["tags"] = rest_info.get("tags", hfhub_info.get("tags", []))

    # Spaces — only REST provides this!
    model_info["spaces"] = rest_info.get("spaces", [])

    # Likes, downloads (REST reliable)
    model_info["likes"] = rest_info.get("likes", hfhub_info.get("likes", 0))
    model_info["downloads"] = rest_info.get("downloads", hfhub_info.get("downloads", 0))

    # Card data (HFHub reliable)
    card_hf = hfhub_info.get("cardData", {})
    card_rest = rest_info.get("cardData", {})

    card = card_rest if isinstance(card_rest, dict) else None
    if card is None:
        card = card_hf if isinstance(card_hf, dict) else {}
    model_info["cardData"] = card

    logger.info(f"CardData keys: {list(card.keys())}")
    # Siblings (REST and HFHub both have this)
    if "siblings" in rest_info:
        model_info["siblings"] = rest_info["siblings"]
    else:
        model_info["siblings"] = [
            {"rfilename": s.rfilename} for s in hfhub_info.get("siblings", [])
        ]

    # Pipeline tag (HFHub mostly)
    model_info["pipeline_tag"] = rest_info.get(
        "pipeline_tag", hfhub_info.get("pipeline_tag")
    )

    # Library name (HFHub)
    model_info["library_name"] = hfhub_info.get("library_name")

    # Private / gated (REST reliable)
    model_info["private"] = rest_info.get("private", hfhub_info.get("private", False))
    model_info["gated"] = rest_info.get("gated", hfhub_info.get("gated", False))

    # Extract datasets from cardData or tags
    card = model_info["cardData"] or {}
    datasets = card.get("datasets")
    if not datasets:
        tags = model_info.get("tags", [])
        dataset_tags = [t.replace("dataset:", "") for t in tags if t.startswith("dataset:")]  # type: ignore[union-attr]
        datasets = dataset_tags if dataset_tags else []
    model_info["datasets"] = datasets

    # -------------------------------------------------------
    # 4. Fetch README via huggingface_hub
    # -------------------------------------------------------
    try:
        readme_url = hf_hub_url(repo_id=model_path, filename="README.md", repo_type="model")
        readme_response = rq.get(readme_url, timeout=15)
        if readme_response.status_code == 200:
            model_readme_text = readme_response.text
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

    # Capture ANY GitHub repo root, even if README link includes tree/blob/etc.
    match = re.search(
        r"(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
        readme_text
    )
    if match:
        return match.group(1)

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
    code_info: dict[str, Any] = {}
    code_readme = ""

    if "github.com" not in code_url:
        return code_info, code_readme

    # Normalize URL to extract only owner/repo
    m = re.search(r"github\.com/([^/]+)/([^/]+)", code_url)
    if not m:
        return code_info, code_readme

    owner, repo = m.groups()
    repo = repo.replace(".git", "")

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
            code_readme = readme_response.text
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


def _extract_model_license(model_info, readme_text: str):
    """Extract license from model metadata or cardData."""
    # Priority 1: cardData.license
    card = model_info.get("cardData", {}) or {}
    lic = card.get("license")
    if isinstance(lic, str) and lic.strip():
        return lic.strip()

    # Priority 2: look at tags: license:mit, license:gpl-3.0, etc.
    tags = model_info.get("tags", [])
    for t in tags:
        if t.lower().startswith("license:"):
            return t.split(":", 1)[1].strip()

    if readme_text:
        readme_license = _extract_license_from_readme(readme_text)
        if readme_license:
            return readme_license

    return None  # unknown license


def _extract_license_from_readme(readme: str) -> str | None:
    """Search README text for license declarations."""
    text = readme.lower()

    # simple direct keywords
    patterns = [
        r"licensed under the ([a-z0-9\.\-\s]+) license",
        r"released under the ([a-z0-9\.\-\s]+) license",
        r"under the ([a-z0-9\.\-\s]+) license",
        r"\bmit license\b",
        r"\bapache license\b",
        r"\bapache 2\.0\b",
        r"\bapachel\s*2\b",
        r"\bgplv?3\b",
        r"\bgplv?2\b",
        r"\blgplv?3\b",
        r"\blgplv?2\.1\b",
        r"\bbsd license\b",
        r"\bcc\-by\-nc\b",
        r"\bcc\-by\b",
    ]

    for pat in patterns:
        match = re.search(pat, text)
        if match:
            # group(1) if available, otherwise whole match
            lic = match.group(1) if match.groups() else match.group(0)
            return lic.strip()

    return None


def compute_model_artifact(
    url: str,
    *,
    artifact_id: Optional[str] = None,
    name_override: Optional[str] = None,
) -> tuple[Artifact, ModelRating, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
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
    code_info: dict[str, Any] = {}
    code_readme: str = ""
    if code_name_hint:
        code_record = memory.find_code_by_name(code_name_hint)
        if code_record:
            code_url = code_record.artifact.data.url
            code_name = code_record.artifact.metadata.name
        else:
            code_name = code_name_hint  # Store the name for future linking
            # Try using the hint URL directly if it's a valid GitHub URL
            if code_repo_hint and 'github.com' in code_repo_hint:
                # Normalize github URLs to repo root
                m = re.search(r"(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", code_repo_hint)
                if m:
                    code_url = m.group(1)
                else:
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
        size_score=SizeScore(**size_scores),
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

    license = _extract_model_license(model_info, readme_text)

    return artifact, rating, dataset_name, dataset_url, code_name, code_url, license
