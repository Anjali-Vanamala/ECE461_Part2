"""
License Metric Calculator for Hugging Face Models.

This module calculates license compatibility scores for machine learning models
from Hugging Face Hub without using the Hugging Face API.
It evaluates whether model licenses are compatible with ACME Corporation's LGPLv2.1 requirements
by directly downloading and analyzing README files.
"""

import re
import time
from typing import Dict, Tuple

import logger  # Import custom logger like performance_claims.py
import requests

# Pre-compiled regex for better performance
URL_PATTERN = re.compile(r'huggingface\.co/([^/]+/[^/?]+)')
LICENSE_HEADER_PATTERN = re.compile(r'^#+\s*licen[cs]e\s*$', re.IGNORECASE | re.MULTILINE)
LICENSE_SECTION_PATTERN = re.compile(
    r'^#+\s*licen[cs]e\s*$(.*?)(?=^#+\s|\Z)',
    re.IGNORECASE | re.MULTILINE | re.DOTALL
)

# Enhanced license patterns to catch more variations
LICENSE_PATTERNS = [
    re.compile(r'licen[cs]e\s*:\s*([^\n]+)', re.IGNORECASE),
    re.compile(r'licen[cs]e["\']?\s*["\']?([^"\'\n]+)["\']?', re.IGNORECASE),
]

COMPATIBLE_LICENSES = {
    "apache-2.0", "apache 2.0", "apache license 2.0", "apache",
    "mit", "mit license",
    "bsd-3-clause", "bsd-3", "bsd 3-clause", "bsd",
    "bsl-1.0", "boost software license",
    "lgpl-2.1", "lgpl 2.1", "lgplv2.1"  # ACME's license is compatible with itself
}

INCOMPATIBLE_LICENSES = {
    "gpl", "gpl-2", "gpl-3", "gplv2", "gplv3", "gnu general public license",
    "agpl", "agpl-3", "affero gpl",
    "lgpl", "lgpl-3", "lgplv3",  # Only LGPLv2.1 is compatible
    "non-commercial", "non commercial", "commercial", "proprietary",
    "creative commons", "cc-by", "cc-by-nc"
}

GATED_INDICATORS = {
    "gated", "gated model", "access request", "request access",
    "apply for access", "application required", "license agreement",
    "terms of use", "terms and conditions", "click through"
}


def extract_model_id_from_url(url: str) -> str:
    """
    Extract model ID from various URL formats.

    Parameters
    ----------
    url : str
        The URL from the input file.

    Returns
    -------
    str
        The extracted model ID.
    """
    match = URL_PATTERN.search(url)
    if match:
        return match.group(1)

    if '/' in url and ' ' not in url and '://' not in url:
        return url

    return url


def download_readme_directly(model_id: str) -> str:
    """
    Download the README.md file directly from Hugging Face without using API.

    Parameters
    ----------
    model_id : str
        The Hugging Face model identifier.

    Returns
    -------
    str
        The content of the README.md file, or empty string if not found.
    """
    try:
        # Try raw content first (most reliable)
        raw_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
        response = requests.get(raw_url, timeout=10)

        if response.status_code == 200:
            logger.info(f"Successfully downloaded README for {model_id}")  # CHANGED: Use logger.info
            return response.text

        # Try alternative URLs
        alternative_urls = [
            f"https://huggingface.co/{model_id}/resolve/main/README.md",
            f"https://huggingface.co/{model_id}/blob/main/README.md",
        ]

        for url in alternative_urls:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully downloaded README for {model_id} from alternative URL")  # CHANGED: Use logger.info
                return response.text

        logger.info(f"README not found for {model_id}")  # CHANGED: Use logger.info
        return ""

    except Exception as e:
        logger.info(f"Error downloading README for {model_id}: {e}")  # CHANGED: Use logger.info
        return ""


def extract_license_section(readme_content: str) -> str:
    """
    Extract the license section from README content.

    Parameters
    ----------
    readme_content : str
        The content of the README.md file.

    Returns
    -------
    str
        The license section text, or empty string if not found.
    """
    if not readme_content:
        return ""

    # Look for license section using header pattern
    license_match = LICENSE_SECTION_PATTERN.search(readme_content)
    if license_match:
        logger.info("Found license section using header pattern")  # CHANGED: Use logger.info
        return license_match.group(1).strip()

    # Try different license patterns
    for pattern in LICENSE_PATTERNS:
        matches = pattern.findall(readme_content)
        if matches:
            logger.info(f"Found license using pattern: {matches[0]}")  # CHANGED: Use logger.info
            return matches[0]

    # Fallback: look for any line containing "license" and take surrounding context
    lines = readme_content.split('\n')
    for i, line in enumerate(lines):
        if re.search(r'licen[cs]e', line, re.IGNORECASE):
            # Get the line and some context
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            logger.info("Found license mention using keyword search")  # CHANGED: Use logger.info
            return '\n'.join(lines[start:end])

    logger.info("No license section found in README")  # CHANGED: Use logger.info
    return ""


def analyze_license_text(license_text: str) -> float:
    """
    Analyze license text and return compatibility score.

    Parameters
    ----------
    license_text : str
        The license text to analyze.

    Returns
    -------
    float
        License score: 1.0 (compatible), 0.0 (incompatible), 0.5 (ambiguous)
    """
    if not license_text:
        logger.info("No license text found - returning 0.0")  # CHANGED: Use logger.info
        return 0.0  # No license information found → incompatible

    text_lower = license_text.lower()

    # Check for gated/commercial licenses first (automatic 0.0)
    if any(indicator in text_lower for indicator in GATED_INDICATORS):
        logger.info("Gated/commercial license detected - returning 0.0")  # CHANGED: Use logger.info
        return 0.0

    # Check for compatible licenses
    compatible_found = False
    compatible_license = ""
    for license in COMPATIBLE_LICENSES:
        if re.search(r'\b' + re.escape(license) + r'\b', text_lower):
            compatible_found = True
            compatible_license = license
            logger.info(f"Compatible license found: {license}")  # CHANGED: Use logger.info
            break

    # Check for incompatible licenses
    incompatible_found = False
    incompatible_license = ""
    for license in INCOMPATIBLE_LICENSES:
        if re.search(r'\b' + re.escape(license) + r'\b', text_lower):
            incompatible_found = True
            incompatible_license = license
            logger.info(f"Incompatible license found: {license}")  # CHANGED: Use logger.info
            break

    # Scoring logic
    if compatible_found and not incompatible_found:
        logger.info(f"Compatible license ({compatible_license}) found without incompatibles - returning 1.0")  # CHANGED: Use logger.info
        return 1.0
    elif incompatible_found:
        logger.info(f"Incompatible license ({incompatible_license}) found - returning 0.0")  # CHANGED: Use logger.info
        return 0.0
    elif compatible_found:
        logger.info(f"Compatible license ({compatible_license}) found (mixed signals) - returning 1.0")  # CHANGED: Use logger.info
        return 1.0  # If compatible found but no incompatible mentioned
    else:
        # Check for common license indicators in the text
        if any(word in text_lower for word in ["apache", "mit", "bsd", "open source", "permissive"]):
            logger.info("Ambiguous but positive license indicators found - returning 0.5")  # CHANGED: Use logger.info
            return 0.5
        else:
            # No clear license found - assume incompatible (more conservative)
            logger.info("No clear license found - returning 0.0")  # CHANGED: Use logger.info
            return 0.0


def get_license_score(model_input) -> Tuple[float, int]:
    """
    Calculate license compatibility score and latency for net scoring.

    Parameters
    ----------
    model_input : str or dict
        The Hugging Face model identifier or model data.

    Returns
    -------
    Tuple[float, int]
        A tuple containing:
        - License compatibility score (0.0-1.0)
        - Latency in milliseconds
    """
    start_time = time.time()

    # Handle input type
    if isinstance(model_input, dict):
        model_id = model_input.get('model_id') or model_input.get('name') or model_input.get('url', '')
        if not model_id:
            latency = int((time.time() - start_time) * 1000)
            logger.info("No model ID found in input - returning 0.0")  # CHANGED: Use logger.info
            return 0.0, latency
    else:
        model_id = model_input

    clean_model_id = extract_model_id_from_url(model_id)
    logger.info(f"Calculating license score for: {clean_model_id}")  # CHANGED: Use logger.info

    # Download and analyze README for unknown models
    readme_content = download_readme_directly(clean_model_id)

    if not readme_content:
        # No README found - assume incompatible
        latency = int((time.time() - start_time) * 1000)
        logger.info(f"No README found for {clean_model_id} - returning 0.0")  # CHANGED: Use logger.info
        return 0.0, latency

    # Extract license section
    license_section = extract_license_section(readme_content)

    # Analyze license text
    score = analyze_license_text(license_section)

    # Calculate actual latency
    latency = int((time.time() - start_time) * 1000)
    logger.info(f"License score calculated: {score} (latency: {latency}ms)")  # CHANGED: Use logger.info

    return score, latency


def get_detailed_license_score(model_input) -> Dict[str, float]:
    """
    Get detailed license score for output formatting (original functionality).

    Parameters
    ----------
    model_input : str or dict
        The Hugging Face model identifier or model data.

    Returns
    -------
    Dict[str, float]
        Dictionary containing license score and latency in milliseconds.
    """
    score, latency = get_license_score(model_input)

    return {
        'license': round(score, 2),  # Round to match sample format
        'license_latency': latency
    }


_license_cache: Dict[str, Tuple[float, int]] = {}


def get_license_score_cached(model_input) -> Tuple[float, int]:
    """
    Cached version to avoid duplicate calculations.
    """
    if isinstance(model_input, dict):
        model_id = model_input.get('model_id') or model_input.get('name') or model_input.get('url', '')
    else:
        model_id = model_input

    if model_id in _license_cache:
        logger.debug(f"Using cached license result for {model_id}")
        return _license_cache[model_id]

    result = get_license_score(model_input)
    _license_cache[model_id] = result
    return result


if __name__ == "__main__":
    test_models = [
        "google-bert/bert-base-uncased",      # Should find Apache 2.0 → 1.0
        "parvk11/audience_classifier_model",  # Unknown license → 0.0 or 0.5
        "openai/whisper-tiny",                # Should find MIT → 1.0
    ]

    logger.info("=== LICENSE ANALYSIS WITHOUT HUGGING FACE API ===")  # CHANGED: Use logger.info

    for model_input in test_models:
        logger.info(f"--- Testing: {model_input} ---")  # CHANGED: Use logger.info

        # Get score and latency for net scoring (returns tuple)
        score, latency = get_license_score_cached(model_input)

        # Get detailed result for output formatting
        detailed_result = get_detailed_license_score(model_input)

        logger.info(f"License score: {score}")  # Use logger.info
        logger.info(f"License latency: {latency} ms")  # Use logger.# info
        logger.info(f"FINAL RESULT: {detailed_result}")  # Use logger.info
