"""
Treescore Metric Calculator for Hugging Face Models.

Calculates the average net score of immediate parent models.
Uses base_model field from Hugging Face metadata to identify parents.

Scoring:
    Average of parent model net scores (0.0-1.0)
    Missing/non-existent parents count as 0.0
    Models with no parents get score 0.0
"""
import json
import time
from typing import Any, Dict, Tuple

from huggingface_hub import hf_hub_download, model_info

import logger

# Cache to avoid recalculating same parent scores
_parent_score_cache: Dict[str, float] = {}

# Maximum number of parents to consider (prevent excessive API calls)
MAX_PARENTS = 5

# Maximum cache size to prevent memory growth
MAX_CACHE_SIZE = 100


def clear_parent_cache() -> None:
    """Clear the parent score cache to free memory."""
    _parent_score_cache.clear()
    logger.debug("Parent score cache cleared")


def _manage_cache_size() -> None:
    """Remove oldest entries if cache exceeds MAX_CACHE_SIZE."""
    if len(_parent_score_cache) > MAX_CACHE_SIZE:
        # Remove oldest 20% of entries (simple FIFO approximation)
        keys_to_remove = list(_parent_score_cache.keys())[:MAX_CACHE_SIZE // 5]
        for key in keys_to_remove:
            del _parent_score_cache[key]
        logger.debug(
            f"Cache size managed: removed {len(keys_to_remove)} entries")


def get_parent_models(model_info_dict: dict) -> list[str]:
    """
    Extract parent model IDs from Hugging Face model info."""
    model_id = model_info_dict.get("id")
    parents = []

    try:
        # Download config.json
        config_path = hf_hub_download(repo_id=str(model_id), filename="config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        logger.debug(f"Loaded config.json {config} for {model_id}")
        # Potential parent fields
        candidate_keys = [
            "base_model_name_or_path",
            "teacher_model_name",
            "student_model_name",
            "source_model",
            "_name_or_path"
        ]

        for key in candidate_keys:
            parent = config.get(key)
            if isinstance(parent, str) and "/" in parent:
                parents.append(parent)
        logger.debug(f"Found parents from config.json: {parents}")

    except Exception as e:
        logger.debug(f"No config.json or parent extraction failed: {e}")

    return parents[:5]


def calculate_parent_net_score(parent_id: str) -> float:
    """
    Calculate net score for a parent model.
    Uses cached results to avoid duplicate calculations.

    Parameters
    ----------
    parent_id : str
        Parent model ID

    Returns
    -------
    float
        Net score (0.0-1.0), or 0.0 if model doesn't exist
    """
    # Check cache first
    if parent_id in _parent_score_cache:
        logger.debug(f"Using cached score for {parent_id}")
        return _parent_score_cache[parent_id]

    try:
        # Get parent model info
        parent_info = model_info(parent_id)

        # Calculate a simple quality score based on available metadata
        # This is a simplified version - in real integration,
        # you'd call the full metric pipeline
        score = 0.0

        # Basic scoring based on model popularity and metadata
        downloads = parent_info.downloads or 0
        likes = parent_info.likes or 0

        # Simple heuristic scoring
        if downloads > 100000:
            score += 0.4
        elif downloads > 10000:
            score += 0.2
        elif downloads > 1000:
            score += 0.1

        if likes > 100:
            score += 0.3
        elif likes > 10:
            score += 0.15

        # Check for good documentation
        if hasattr(parent_info, 'cardData') and parent_info.cardData:
            score += 0.3

        score = min(score, 1.0)  # Cap at 1.0

        logger.debug(f"Calculated score for {parent_id}: {score}")

        # Cache the result
        _parent_score_cache[parent_id] = score

        # Manage cache size
        _manage_cache_size()

        return score

    except Exception as e:
        logger.info(f"Error getting info for parent {parent_id}: {e}")
        # Count missing parents as 0
        _parent_score_cache[parent_id] = 0.0
        return 0.0


def treescore(model_info_dict: Dict[str, Any]) -> Tuple[float, float]:
    """
    Calculate treescore as average of parent model scores.

    Parameters
    ----------
    model_info_dict : dict
        Model information from Hugging Face API

    Returns
    -------
    Tuple[float, float]
        Treescore (0.0-1.0) and latency in milliseconds
    """
    start = time.time()
    logger.info("Calculating treescore metric")

    try:
        # Get parent models
        parents = get_parent_models(model_info_dict)

        if not parents:
            logger.info("No parent models found - score: 0.0")
            score = 0.0
        else:
            logger.info(f"Found {len(parents)} parent model(s)")

            # Calculate scores for each parent
            parent_scores = []
            for parent_id in parents:
                parent_score = calculate_parent_net_score(parent_id)
                parent_scores.append(parent_score)
                logger.debug(f"Parent {parent_id}: {parent_score}")

            # Average the scores
            score = sum(parent_scores) / len(parent_scores)
            logger.info(f"Average parent score: {score}")

    except Exception as e:
        logger.info(f"Error calculating treescore: {e}")
        score = 0.0

    end = time.time()
    latency = int((end - start) * 1000)

    logger.info(f"Treescore: {score}, latency: {latency}ms")

    return round(score, 2), latency
