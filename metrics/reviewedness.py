"""
Reviewedness Metric Calculator.

Measures the fraction of LOC introduced via reviewed pull requests.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Tuple

import requests

import logger

# -----------------------------
# GitHub Auth
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "ece461-model-registry",
}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


# -----------------------------
# Rate Limiting
# -----------------------------
RATE_LIMIT_DELAY = 0.15
_last_call_time = 0.0


def _rate_limit() -> None:
    global _last_call_time
    now = time.time()
    delta = now - _last_call_time
    if delta < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - delta)
    _last_call_time = time.time()


# -----------------------------
# Fetch merged PRs (list)
# -----------------------------
def _get_merged_prs(full_name: str) -> list[dict[str, Any]]:
    """
    Fetch up to the 10 most recent merged PRs from a GitHub repo.
    """
    url = f"https://api.github.com/repos/{full_name}/pulls"
    params = {
        "state": "closed",
        "per_page": 100,  # fetch 100 at a time
        "sort": "created",
        "direction": "desc",
    }  # type: ignore

    prs = []  #type: ignore
    page = 1

    while len(prs) < 10:
        _rate_limit()
        try:
            r = requests.get(url, headers=GITHUB_HEADERS,
                             params={**params, "page": page}, timeout=15)  # type: ignore
        except requests.RequestException as e:
            logger.info(f"GitHub API request failed: {e}")
            break

        if r.status_code != 200:
            logger.info(f"GitHub API returned {r.status_code}: {r.text}")
            break

        items = r.json()
        if not items:
            break

        merged_items = [p for p in items if p.get("merged_at")]
        prs.extend(merged_items)
        if len(merged_items) == 0:
            # No more merged PRs in this page
            break

        page += 1

    # Only return up to 10 PRs
    prs = prs[:10]
    logger.info(f"Total merged PRs fetched: {len(prs)}")
    return prs


# -----------------------------
# Individual PR LOC + reviews
# -----------------------------


_pr_loc_cache: Dict[int, int] = {}
_review_cache: Dict[int, bool] = {}


def _get_pr_details(full_name: str, number: int) -> Tuple[int, bool]:
    """Fetches LOC and review state for a PR with caching."""

    if number in _pr_loc_cache and number in _review_cache:
        return _pr_loc_cache[number], _review_cache[number]
    logger.info(f"Fetching PR #{number} details...")

    url = f"https://api.github.com/repos/{full_name}/pulls/{number}"
    _rate_limit()
    r = requests.get(url, headers=GITHUB_HEADERS, timeout=10)
    if r.status_code != 200:
        logger.info(f"Failed PR #{number}: {r.status_code}")
        return 0, False

    data = r.json()
    loc = data.get("additions", 0)

    # Detect reviewed via summary fields
    reviewed = (data.get("review_comments", 0) > 0 or data.get("comments", 0) > 0)
    logger.info(f"PR #{number}: LOC={loc}, reviewed={reviewed}")

    _pr_loc_cache[number] = loc
    _review_cache[number] = reviewed
    return loc, reviewed


# -----------------------------
# Main computation
# -----------------------------
def compute_reviewed_fraction(code_info: Dict[str, Any]) -> float:
    if not code_info or "full_name" not in code_info:
        return -1.0

    full_name = code_info["full_name"]
    merged_prs = _get_merged_prs(full_name)

    if not merged_prs:
        return 0.0

    # 🔥 LIMIT TO MOST RECENT 50 MERGED PRs
    merged_prs = merged_prs[:10]

    total_loc = 0
    reviewed_loc = 0

    for pr in merged_prs:
        number = pr["number"]
        loc, reviewed = _get_pr_details(full_name, number)

        total_loc += loc
        if reviewed:
            reviewed_loc += loc

    if total_loc == 0:
        return 0.0

    return reviewed_loc / total_loc


# -----------------------------
# Final wrapper
# -----------------------------


def reviewedness(code_info: Dict[str, Any]) -> Tuple[float, int]:
    start = time.time()
    fraction = compute_reviewed_fraction(code_info)

    # 🔥 Score is directly the fraction
    score = fraction

    logger.info(f"Reviewedness score: {score} (fraction: {fraction})")
    return round(score, 2), int((time.time() - start) * 1000)
