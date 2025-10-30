"""
Treescore Metric Calculator for Hugging Face Models.

Calculates the average net score of immediate parent models.
Uses base_model field from Hugging Face metadata to identify parents.

Scoring:
    Average of parent model net scores (0.0-1.0)
    Missing/non-existent parents count as 0.0
    Models with no parents get score 0.0
"""

import time
from typing import Any, Dict, List, Tuple

import logger
from huggingface_hub import model_info

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


def get_parent_models(model_info_dict: Dict[str, Any]) -> List[str]:
    """
    Extract parent model IDs from model metadata.

    Parameters
    ----------
    model_info_dict : dict
        Model information from Hugging Face API

    Returns
    -------
    List[str]
        List of parent model IDs
    """
    if not model_info_dict:
        logger.debug("No model_info provided")
        return []

    parents = []

    # Check for base_model in cardData
    card_data = model_info_dict.get('cardData', {})
    base_model = card_data.get('base_model')

    if base_model:
        # base_model can be string or list
        if isinstance(base_model, str):
            parents.append(base_model)
            logger.debug(f"Found base_model: {base_model}")
        elif isinstance(base_model, list):
            parents.extend(base_model[:MAX_PARENTS])
            logger.debug(f"Found {len(base_model)} base_models")

    # Limit to MAX_PARENTS
    return parents[:MAX_PARENTS]


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


def treescore(model_info_dict: Dict[str, Any]) -> Tuple[float, int]:
    """
    Calculate treescore as average of parent model scores.

    Parameters
    ----------
    model_info_dict : dict
        Model information from Hugging Face API

    Returns
    -------
    Tuple[float, int]
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
