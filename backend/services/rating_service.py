"""
Service to calculate package metrics using Phase 1 metrics.
Integrates with metric_concurrent and ingestion.
"""
import os
import re
import sys
from typing import Any, Dict
from urllib.parse import urlparse

import requests as rq

import logger
import metric_concurrent
from backend.models.package import PackageModel


def calculate_package_metrics(model_url: str) -> PackageModel:
    """
    Calculate all metrics for a package given a HuggingFace model URL.
    Returns a PackageModel with all scores and latencies.
    """
    model_readme = ""
    dataset_readme = ""
    code_readme = ""
    model_info: Dict[str, Any] = {}
    code_info: Dict[str, Any] = {}
    seen_datasets: set[str] = set()

    logger.debug(f"\nBegin processing model URL: {model_url}")
    
    # Parse model URL
    parsed_model = urlparse(model_url)
    model_path = parsed_model.path.strip('/')
    parts = model_path.split("/")
    if "tree" in parts:
        tree_index = parts.index("tree")
        model_path = "/".join(parts[:tree_index])
    
    # Get model info from API
    model_api_url = f'https://huggingface.co/api/models/{model_path}'
    try:
        api_response = rq.get(model_api_url)
        if api_response.status_code == 200:
            model_info = api_response.json()
    except Exception as e:
        logger.debug(f"Failed to get model info: {e}")
        model_info = {}
    
    # Get model README
    model_rm_url = f"https://huggingface.co/{model_path}/raw/main/README.md"
    try:
        model_readme_response = rq.get(model_rm_url, timeout=50)
        if model_readme_response.status_code == 200:
            model_readme = model_readme_response.text.lower()
    except Exception as e:
        logger.debug(f"Failed to get model README: {e}")
        model_readme = ""
    
    # Extract model ID and name
    model_id = model_info.get("id", model_path.split("/")[-1] if "/" in model_path else model_path)
    model_name = model_id.split("/")[-1] if "/" in model_id else model_id
    
    # For now, we'll use empty dataset and code URLs
    # In a full implementation, these could be passed as parameters
    raw_dataset_url = ""
    raw_code_url = ""
    
    # Get code info if code URL provided (for future enhancement)
    if raw_code_url:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', raw_code_url)
        if match:
            owner, repo = match.groups()
            repo = repo.replace('.git', '')
            code_url = f"https://api.github.com/repos/{owner}/{repo}"
            try:
                api_response = rq.get(code_url)
                if api_response.status_code == 200:
                    code_info = api_response.json()
            except Exception:
                code_info = {}
            try:
                code_readme_response = rq.get(f"{code_url}/readme", headers={'Accept': 'application/vnd.github.v3.raw'})
                if code_readme_response.status_code == 200:
                    code_readme = code_readme_response.text.lower()
            except Exception:
                code_readme = ""
    
    # Calculate all metrics using metric_concurrent
    # We'll extract the data by calling the internal logic directly
    import time
    from concurrent.futures import Future, ThreadPoolExecutor, as_completed

    from metrics.bus_factor import bus_factor
    from metrics.code_quality import code_quality
    from metrics.data_quality import data_quality
    from metrics.dataset_and_code_score import dataset_and_code_score
    from metrics.license import get_license_score
    from metrics.performance_claims import performance_claims
    from metrics.ramp_up_time import ramp_up_time
    from metrics.reproducibility import reproducibility
    from metrics.reviewedness import reviewedness
    from metrics.size import calculate_size_score
    from metrics.treescore import treescore
    
    start = time.time()
    logger.info("Begin processing metrics.")
    
    results: Dict[str, Any] = {}
    
    with ThreadPoolExecutor() as executor:
        future_to_metric: Dict[Future, str] = {  # type: ignore[type-arg]
            executor.submit(data_quality, model_info, model_readme): "data_quality",
            executor.submit(code_quality, model_info, code_info, model_readme, code_readme): "code_quality",
            executor.submit(dataset_and_code_score, code_info, raw_dataset_url, model_readme): "dc_score",
            executor.submit(performance_claims, model_url): "performance_claims",
            executor.submit(calculate_size_score, model_url): "size_score",
            executor.submit(get_license_score, model_url): "license_score",
            executor.submit(bus_factor, model_info): "bus_factor",
            executor.submit(ramp_up_time, model_info): "ramp_up_time",
            executor.submit(reproducibility, model_info, code_info, model_readme): "reproducibility",
            executor.submit(reviewedness, code_info): "reviewedness",
            executor.submit(treescore, model_info): "treescore",
        }
        
        for future in as_completed(future_to_metric):
            metric_name: str = future_to_metric[future]
            try:
                results[metric_name] = future.result()
            except Exception as e:
                logger.debug(f"{metric_name} failed with error: {e}")
                results[metric_name] = None
    
    # Helper function to convert latency to milliseconds (integer)
    def to_ms(latency):
        """Convert latency to milliseconds as integer"""
        if latency is None:
            return 0
        # If latency is already in milliseconds (> 1000 or reasonable assumption)
        # Otherwise assume it's in seconds and convert
        if latency < 1.0:  # Likely in seconds, convert to milliseconds
            return int(latency * 1000)
        else:  # Already in milliseconds or large value
            return int(latency)
    
    # Unpack the results with error handling
    try:
        result = results.get("data_quality")
        if result is None:
            data_quality_score, dq_latency = 0.0, 0
        else:
            data_quality_score, dq_latency_raw = result
            dq_latency = to_ms(dq_latency_raw)
    except (TypeError, ValueError, AttributeError):
        data_quality_score, dq_latency = 0.0, 0
    
    try:
        result = results.get("code_quality")
        if result is None:
            code_quality_score, cq_latency = 0.0, 0
        else:
            code_quality_score, cq_latency_raw = result
            cq_latency = to_ms(cq_latency_raw)
    except (TypeError, ValueError, AttributeError):
        code_quality_score, cq_latency = 0.0, 0
    
    try:
        result = results.get("dc_score")
        if result is None:
            dc_score, dc_latency = 0.0, 0
        else:
            dc_score, dc_latency_raw = result
            # dataset_and_code_score already returns milliseconds
            dc_latency = int(dc_latency_raw) if dc_latency_raw else 0
    except (TypeError, ValueError, AttributeError):
        dc_score, dc_latency = 0.0, 0
    
    try:
        result = results.get("performance_claims")
        if result is None:
            perf_score, perf_latency = 0.0, 0
        else:
            perf_score, perf_latency_raw = result
            # performance_claims already returns milliseconds
            perf_latency = int(perf_latency_raw) if perf_latency_raw else 0
    except (TypeError, ValueError, AttributeError):
        perf_score, perf_latency = 0.0, 0
    
    try:
        result = results.get("size_score")
        if result is None:
            size_scores, net_size_score, size_latency = {}, 0.0, 0
        else:
            size_scores, net_size_score, size_latency_raw = result
            size_latency = to_ms(size_latency_raw)
    except (TypeError, ValueError, AttributeError):
        size_scores, net_size_score, size_latency = {}, 0.0, 0
    
    try:
        result = results.get("license_score")
        if result is None:
            license_score, license_latency = 0.0, 0
        else:
            license_score, license_latency_raw = result
            license_latency = to_ms(license_latency_raw)
    except (TypeError, ValueError, AttributeError):
        license_score, license_latency = 0.0, 0
    
    try:
        result = results.get("bus_factor")
        if result is None:
            bus_score, bus_latency = 0.0, 0
        else:
            bus_score, bus_latency_raw = result
            bus_latency = to_ms(bus_latency_raw)
    except (TypeError, ValueError, AttributeError):
        bus_score, bus_latency = 0.0, 0
    
    try:
        result = results.get("ramp_up_time")
        if result is None:
            ramp_score, ramp_latency = 0.0, 0
        else:
            ramp_score, ramp_latency_raw = result
            ramp_latency = to_ms(ramp_latency_raw)
    except (TypeError, ValueError, AttributeError):
        ramp_score, ramp_latency = 0.0, 0
    
    try:
        result = results.get("reproducibility")
        if result is None:
            repro_score, repro_latency = 0.0, 0
        else:
            repro_score, repro_latency_raw = result
            repro_latency = to_ms(repro_latency_raw)
    except (TypeError, ValueError, AttributeError):
        repro_score, repro_latency = 0.0, 0
    
    try:
        result = results.get("reviewedness")
        if result is None:
            review_score, review_latency = 0.0, 0
        else:
            review_score, review_latency_raw = result
            review_score = max(0.0, review_score)
            review_latency = to_ms(review_latency_raw)
    except (TypeError, ValueError, AttributeError):
        review_score, review_latency = 0.0, 0
    
    try:
        result = results.get("treescore")
        if result is None:
            tree_score, tree_latency = 0.0, 0
        else:
            tree_score, tree_latency_raw = result
            tree_latency = to_ms(tree_latency_raw)
    except (TypeError, ValueError, AttributeError):
        tree_score, tree_latency = 0.0, 0
    
    # Calculate net score
    net_score: float = (
        0.09 * license_score + 0.10 * ramp_score + 0.11 * net_size_score +
        0.13 * data_quality_score + 0.10 * bus_score + 0.13 * dc_score +
        0.10 * code_quality_score + 0.09 * perf_score + 0.05 * repro_score +
        0.05 * review_score + 0.05 * tree_score
    )
    
    end = time.time()
    net_latency: int = int((end - start) * 1000)
    
    # Handle size_score format - convert dict to expected format
    if isinstance(size_scores, dict):
        size_score_dict = size_scores
    else:
        size_score_dict = {"value": net_size_score, "unit": "MB"}
    
    # Create package model with all metrics
    package = PackageModel(
        id=model_id,
        name=model_name,
        category="MODEL",
        URL=model_url,
        description=model_info.get("cardData", {}).get("description", ""),
        net_score=round(net_score, 2),
        ramp_up_time=round(ramp_score, 2),
        bus_factor=round(bus_score, 2),
        performance_claims=round(perf_score, 2),
        license=round(license_score, 2),
        dataset_and_code_score=round(dc_score, 2),
        dataset_quality=round(data_quality_score, 2),
        code_quality=round(code_quality_score, 2),
        reproducibility=round(repro_score, 2),
        reviewedness=round(review_score, 2),
        treescore=round(tree_score, 2),
        size_score=size_score_dict,
        net_score_latency=net_latency,
        ramp_up_time_latency=ramp_latency,
        bus_factor_latency=bus_latency,
        performance_claims_latency=perf_latency,
        license_latency=license_latency,
        size_score_latency=size_latency,
        dataset_and_code_score_latency=dc_latency,
        dataset_quality_latency=dq_latency,
        code_quality_latency=cq_latency,
        reproducibility_latency=repro_latency,
        reviewedness_latency=review_latency,
        treescore_latency=tree_latency
    )
    
    return package

