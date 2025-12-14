"""
Lineage extraction service for HuggingFace models.

Extracts dependency information (base models, datasets) from HuggingFace metadata
to build lineage graphs.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def extract_model_id_from_url(url: str) -> Optional[str]:
    """
    Extract HuggingFace model ID from URL.

    Examples:
        https://huggingface.co/bert-base-uncased -> bert-base-uncased
        https://huggingface.co/openai/whisper-tiny -> openai/whisper-tiny
    """
    import re
    pattern = r'huggingface\.co/(?:models/)?([^/]+/[^/?]+|[^/?]+)'
    match = re.search(pattern, url)
    if match:
        model_id = match.group(1)
        # Remove /tree/main or similar suffixes
        if '/tree' in model_id:
            model_id = model_id.split('/tree')[0]
        return model_id
    return None


def fetch_huggingface_config(model_id: str) -> Optional[Dict]:
    """
    Fetch config.json from HuggingFace for a model.

    Args:
        model_id: HuggingFace model identifier (e.g., 'bert-base-uncased' or 'openai/whisper-tiny')

    Returns:
        Dictionary containing config.json contents, or None if not available.
    """
    try:
        # Try to fetch config.json from HuggingFace
        config_url = f"https://huggingface.co/{model_id}/resolve/main/config.json"
        logger.info(f"Fetching config.json from {config_url}")

        response = requests.get(config_url, timeout=10, allow_redirects=True)

        if response.status_code == 200:
            config = response.json()
            logger.info(f"Successfully fetched config.json for {model_id}")
            return config
        else:
            logger.warning(f"Failed to fetch config.json for {model_id}: HTTP {response.status_code}")
            return None

    except requests.RequestException as e:
        logger.warning(f"Network error fetching config.json for {model_id}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching config.json for {model_id}: {e}")
        return None


def extract_lineage_from_config(config: Dict) -> Tuple[Optional[str], List[str], Dict[str, str]]:
    """
    Extract lineage information from HuggingFace config.json.

    Args:
        config: Parsed config.json dictionary

    Returns:
        Tuple of:
        - base_model_name: Name of parent/base model (if any)
        - dataset_names: List of dataset names used
        - metadata: Additional metadata for lineage graph
    """
    base_model_name: Optional[str] = None
    dataset_names: List[str] = []
    metadata: Dict[str, str] = {}

    # Extract base model (multiple possible keys)
    # Order matters: more specific keys first
    base_model_keys = [
        'base_model',
        'base_model_name_or_path',
        'base_model_revision',
        '_name_or_path',
        'model_name_or_path',
        'pretrained_model_name_or_path',
        'model_type',  # Sometimes contains parent model name
    ]

    for key in base_model_keys:
        if key in config and config[key]:
            value = config[key]
            # Only use if it looks like a model name (not a local path)
            if isinstance(value, str):
                value_lower = value.lower()
                # Skip local paths and special keywords
                starts_with_path = value.startswith('.') or value.startswith('/') or value.startswith('\\')
                is_windows_path = ':' in value[:3]
                is_special_keyword = value_lower in ['auto', 'none', 'null', '']
                matches_model_type = value_lower == config.get('model_type', '').lower()
                is_local_path = starts_with_path or is_windows_path or is_special_keyword or matches_model_type

                if not is_local_path:
                    base_model_name = value
                    metadata['base_model_source'] = key
                    logger.info(f"Found base model: {base_model_name} (from {key})")
                    break

    # Extract dataset information
    if 'datasets' in config:
        datasets = config['datasets']
        if isinstance(datasets, list):
            dataset_names = [str(d) for d in datasets if d]
        elif isinstance(datasets, str):
            dataset_names = [datasets]

        if dataset_names:
            logger.info(f"Found datasets: {dataset_names}")

    # Store additional metadata
    if 'model_type' in config:
        metadata['model_type'] = str(config['model_type'])

    if 'architectures' in config and isinstance(config['architectures'], list):
        metadata['architecture'] = ','.join(str(a) for a in config['architectures'])

    return base_model_name, dataset_names, metadata


def extract_lineage_from_url(url: str) -> Tuple[Optional[str], List[str], Dict[str, str]]:
    """
    Extract lineage information from a HuggingFace model URL.

    This is the main entry point for lineage extraction.

    Args:
        url: HuggingFace model URL or ID

    Returns:
        Tuple of (base_model_name, dataset_names, metadata)
    """
    # Check if URL is HuggingFace
    if 'huggingface.co' not in url and '/' not in url:
        logger.info(f"URL {url} is not a HuggingFace model, skipping lineage extraction")
        return None, [], {}

    # Extract model ID from URL
    model_id = extract_model_id_from_url(url)
    if not model_id:
        # Try using the URL as-is if it looks like a model ID
        if '/' in url and ' ' not in url and '://' not in url:
            model_id = url
        else:
            logger.warning(f"Could not extract model ID from URL: {url}")
            return None, [], {}

    # Fetch and parse config.json
    config = fetch_huggingface_config(model_id)
    if not config:
        logger.info(f"No config.json available for {model_id}")
        return None, [], {}

    # Extract lineage from config
    base_model, datasets, metadata = extract_lineage_from_config(config)

    # Add repository URL to metadata
    metadata['repository_url'] = f"https://huggingface.co/{model_id}"

    return base_model, datasets, metadata
