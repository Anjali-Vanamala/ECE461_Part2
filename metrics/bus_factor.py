# from parse_categories import masterScoring
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple
from metrics_helpers.get_github_url import extract_github_url
import requests
import logger


def calculate_active_maintenance_score(api_info: Dict[str, Any]) -> float:
    """
    Calculate active maintenance score based on the creation date and last updated date

    Parameters
    ----------
    api_info : dict
        Dictionary with information about the API

    Returns
    -------
    float
        Active maintenance score (0-1)
    """
    last_modified = api_info.get("lastModified")

    if not last_modified:
        logger.debug("API Info has no information about dates.")
        return 0.0

    # created_at and last_modified expected to be ISO strings; ensure they are strings
    modified_date = datetime.fromisoformat(str(last_modified).replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    days_since_modified = (now - modified_date).days

    if days_since_modified < 90:
        update_score: float = 1.0
    elif days_since_modified < 180:
        update_score = 0.8
    elif days_since_modified < 270:
        update_score = 0.6
    elif days_since_modified < 365:
        update_score = 0.4
    else:
        update_score = 0.2

    return update_score


def calculate_contributor_diversity_score(api_info: Dict[str, Any]) -> float:
    """
    Calculate contributor diversity score based on actual GitHub contributors
    if possible. Falls back to using HuggingFace 'spaces' list otherwise.

    Scoring: min(num_contributors / 10, 1.0)
    """

    # ---------------------------------------
    # 1. Try to get GitHub repo URL
    # ---------------------------------------
    github_url = extract_github_url(api_info)
    print(github_url)
    if github_url:
        # Example: https://github.com/org/repo
        try:
            owner, repo = github_url.rstrip("/").split("/")[-2:]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"

            # Optional: Add a GitHub token header here to avoid rate limits
            resp = requests.get(api_url, timeout=5)
            print(resp)
            if resp.status_code == 200:
                contributors = resp.json()
                print(resp.json())
                # GitHub returns a list of contributor objects
                if isinstance(contributors, list):
                    num_contributors = len(contributors)
                    return min(num_contributors / 10.0, 1.0)

        except Exception:
            pass  
    fallback_contributors = 0.5

    return min(fallback_contributors / 10.0, 1.0)


def calculate_org_backing_score(api_info: Dict[str, Any]) -> float:
    """
    Calculate organizational backing score based on if the organization falls in the list of known orgs

    Parameters
    ----------
    api_info : dict
        Dictionary with information about the API

    Returns
    -------
    float
        Organizational backing score (0-1)
    """

    KNOWN_ORGS = {"google", "meta", "microsoft", "openai", "apple", "ibm", "huggingface"}

    author = api_info.get("author", "").lower()
    if any(org in author for org in KNOWN_ORGS):
        return 1.0
    elif author:
        return 0.5
    else:
        return 0.0


def bus_factor(api_info: Dict[str, Any]) -> Tuple[float, float]:
    """
    Calculate bus factor (higher score is better).

    Parameters
    ----------
    contributor_diversity_score : float
        Contributor diversity score (0-1)
    active_maintenance_score : float
        Active maintenance score (0-1)
    org_backing_score : float
        Org backing score (0-1)

    Returns
    -------
    float
        Bus Factor metric score (0-1)
    """

    logger.info(" Calculating bus factor metric")

    # start latency timer
    start = time.perf_counter()

    contributor_diversity_score: float = calculate_contributor_diversity_score(api_info)
    active_maintenance_score: float = calculate_active_maintenance_score(api_info)
    org_backing_score: float = calculate_org_backing_score(api_info)

    bus_factor_metric_score: float = (0.55 * contributor_diversity_score + 0.2 * active_maintenance_score + 0.25 * org_backing_score)

    # end latency timer
    end = time.perf_counter()

    latency: float = (end - start) * 1000

    return round(bus_factor_metric_score, 2), latency
