"""
Reviewedness Metric Calculator for GitHub Repositories.

Calculates the fraction of code introduced via reviewed pull requests.
Only considers PRs from the last 2 years.

Scoring:
    1.0 - 80%+ of PRs are reviewed
    0.5 - 50-80% of PRs are reviewed
    0.0 - <50% of PRs are reviewed, or no GitHub repo
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

import requests

import logger

# Rate limiting constants
RATE_LIMIT_DELAY = 0.1  # 100ms between API calls
_last_api_call_time = 0.0


def _rate_limit() -> None:
    """Ensure we don't exceed GitHub API rate limits."""
    global _last_api_call_time
    current_time = time.time()
    time_since_last = current_time - _last_api_call_time

    if time_since_last < RATE_LIMIT_DELAY:
        sleep_time = RATE_LIMIT_DELAY - time_since_last
        time.sleep(sleep_time)

    _last_api_call_time = time.time()


def get_reviewed_pr_fraction(code_info: Dict[str, Any]) -> float:
    """
    Calculate fraction of reviewed PRs from last 2 years.

    Parameters
    ----------
    code_info : dict
        GitHub repository information

    Returns
    -------
    float
        Fraction of reviewed PRs (0.0-1.0)
    """
    if not code_info or not code_info.get('full_name'):
        logger.debug("No GitHub repository information")
        return -1.0

    full_name = code_info.get('full_name')
    api_url = f"https://api.github.com/repos/{full_name}/pulls"

    try:
        # Get PRs from last 2 years
        two_years_ago = datetime.now() - timedelta(days=730)

        # Get closed PRs (merged or not)
        params: Dict[str, str] = {
            'state': 'closed',
            'per_page': '100',  # Get up to 100 PRs
            'sort': 'updated',
            'direction': 'desc'
        }

        _rate_limit()  # Rate limit before API call
        response = requests.get(api_url, params=params, timeout=10)

        if response.status_code != 200:
            logger.info(f"GitHub API error: {response.status_code}")
            return 0.0

        prs = response.json()

        # Filter PRs from last 2 years
        recent_prs = []
        for pr in prs:
            created_at = datetime.strptime(
                pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            if created_at >= two_years_ago:
                recent_prs.append(pr)

        if not recent_prs:
            logger.info("No PRs found in last 2 years")
            return 0.0  # No recent PRs, so cannot measure review practices

        logger.info(f"Found {len(recent_prs)} PRs in last 2 years")

        # Count reviewed PRs
        reviewed_count = 0
        for pr in recent_prs:
            # Check if PR has reviews
            reviews_url = pr.get('url') + '/reviews'
            _rate_limit()  # Rate limit before each review check
            reviews_response = requests.get(reviews_url, timeout=10)

            if reviews_response.status_code == 200:
                reviews = reviews_response.json()
                if len(reviews) > 0:
                    reviewed_count += 1
                    logger.debug(
                        f"PR #{pr['number']} has {len(reviews)} reviews")

        fraction = reviewed_count / len(recent_prs)
        logger.info(
            f"Reviewed PRs: {reviewed_count}/{len(recent_prs)} "
            f"({fraction:.2%})")

        return fraction

    except Exception as e:
        logger.info(f"Error getting PR data: {e}")
        return 0.0


def reviewedness(code_info: Dict[str, Any]) -> Tuple[float, int]:
    """
    Calculate reviewedness score based on reviewed PR fraction.

    Parameters
    ----------
    code_info : dict
        GitHub repository information

    Returns
    -------
    Tuple[float, int]
        Reviewedness score (0.0-1.0) and latency in milliseconds
    """
    start = time.time()
    logger.info("Calculating reviewedness metric")

    try:
        fraction = get_reviewed_pr_fraction(code_info)

        # Score based on review fraction
        if fraction == -1.0:
            score = -1.0 
            logger.info(f"No GitHub repo - score: -1.0")
        elif fraction >= 0.8:
            score = 1.0
            logger.info(f"High review rate ({fraction:.2%}) - score: 1.0")
        elif fraction >= 0.5:
            score = 0.5
            logger.info(f"Moderate review rate ({fraction:.2%}) - score: 0.5")
        else:
            score = 0.0
            logger.info(f"Low review rate ({fraction:.2%}) - score: 0.0")

    except Exception as e:
        logger.info(f"Error calculating reviewedness: {e}")
        score = 0.0

    end = time.time()
    latency = int((end - start) * 1000)

    logger.info(f"Reviewedness score: {score}, latency: {latency}ms")

    return round(score, 2), latency
