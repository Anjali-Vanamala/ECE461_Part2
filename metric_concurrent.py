"""
Concurrent evaluation of ML model metrics.

This module computes various metrics for a machine learning model,
its associated code, and dataset in parallel using threads. Metrics
include data quality, code quality, license, performance claims,
bus factor, ramp-up time, reproducibility, and more.

The main function returns a list of computed scores and prints
a detailed evaluation using `print_model_evaluation`.
"""

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Dict

import logger
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
from print_metrics import print_model_evaluation


def main(
    model_info: Any,
    model_readme: Any,
    raw_model_url: str,
    code_info: Any,
    code_readme: Any,
    raw_dataset_url: str,
    *,
    dataset_name: str | None = None,
    code_name: str | None = None
) -> list[float]:
    """
    Compute multiple model evaluation metrics concurrently.

    Parameters
    ----------
    model_info : Any
        Metadata dictionary about the model (from API or other sources).
    model_readme : Any
        Model README text content.
    raw_model_url : str
        URL of the model repository.
    code_info : Any
        Metadata dictionary about the code repository.
    code_readme : Any
        README content for the code repository.
    raw_dataset_url : str
        URL of the dataset repository.
    dataset_name : str, optional
        Hint for dataset name to use in metric calculations.
    code_name : str, optional
        Hint for code repository name to use in metric calculations.

    Returns
    -------
    list[float]
        Ordered list of metric scores:
        [net_size_score, license_score, ramp_score, bus_score, dc_score,
         data_quality_score, code_quality_score, perf_score, repro_score,
         review_score, tree_score]
    """
    start = time.time()
    logger.info("Begin processing metrics.")
    if dataset_name:
        logger.debug(f"Dataset hint supplied to metrics: {dataset_name}")
    if code_name:
        logger.debug(f"Code hint supplied to metrics: {code_name}")

    results: Dict[str, Any] = {}

    with ThreadPoolExecutor() as executor:
        future_to_metric: Dict[Future, str] = {
            executor.submit(data_quality, model_info, model_readme): "data_quality",
            executor.submit(code_quality, model_info, code_info, model_readme, code_readme): "code_quality",
            executor.submit(
                dataset_and_code_score,
                code_info,
                raw_dataset_url,
                model_readme,
                dataset_name=dataset_name
            ): "dc_score",
            executor.submit(performance_claims, raw_model_url): "performance_claims",
            executor.submit(calculate_size_score, raw_model_url): "size_score",
            executor.submit(get_license_score, raw_model_url): "license_score",
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

    # Unpack the results with error handling for None values
    data_quality_score: float
    dq_latency: int
    code_quality_score: float
    cq_latency: int
    dc_score: float
    dc_latency: int
    perf_score: float
    perf_latency: int
    size_scores: Any
    net_size_score: float
    size_latency: int
    license_score: float
    license_latency: int
    bus_score: float
    bus_latency: int
    ramp_score: float
    ramp_latency: int
    repro_score: float
    repro_latency: int
    review_score: float
    review_latency: int
    tree_score: float
    tree_latency: int

    # Unpack results with None checking
    result_data_quality = results.get("data_quality")
    if result_data_quality is None:
        data_quality_score, dq_latency = 0.0, 0
    else:
        try:
            data_quality_score, dq_latency = result_data_quality
        except (TypeError, ValueError):
            data_quality_score, dq_latency = 0.0, 0

    result_code_quality = results.get("code_quality")
    if result_code_quality is None:
        code_quality_score, cq_latency = 0.0, 0
    else:
        try:
            code_quality_score, cq_latency = result_code_quality
        except (TypeError, ValueError):
            code_quality_score, cq_latency = 0.0, 0

    result_dc_score = results.get("dc_score")
    if result_dc_score is None:
        dc_score, dc_latency = 0.0, 0
    else:
        try:
            dc_score, dc_latency = result_dc_score
        except (TypeError, ValueError):
            dc_score, dc_latency = 0.0, 0

    result_perf = results.get("performance_claims")
    if result_perf is None:
        perf_score, perf_latency = 0.0, 0
    else:
        try:
            perf_score, perf_latency = result_perf
        except (TypeError, ValueError):
            logger.debug("GenAI query failed to produce a result")
            perf_score, perf_latency = 0.0, 0

    result_size = results.get("size_score")
    if result_size is None:
        size_scores, net_size_score, size_latency = {}, 0.0, 0
    else:
        try:
            size_scores, net_size_score, size_latency = result_size
        except (TypeError, ValueError):
            size_scores, net_size_score, size_latency = {}, 0.0, 0

    result_license = results.get("license_score")
    if result_license is None:
        license_score, license_latency = 0.0, 0
    else:
        try:
            license_score, license_latency = result_license
        except (TypeError, ValueError):
            license_score, license_latency = 0.0, 0

    result_bus = results.get("bus_factor")
    if result_bus is None:
        bus_score, bus_latency = 0.0, 0
    else:
        try:
            bus_score, bus_latency = result_bus
        except (TypeError, ValueError):
            bus_score, bus_latency = 0.0, 0

    result_ramp = results.get("ramp_up_time")
    if result_ramp is None:
        ramp_score, ramp_latency = 0.0, 0
    else:
        try:
            ramp_score, ramp_latency = result_ramp
        except (TypeError, ValueError):
            ramp_score, ramp_latency = 0.0, 0

    result_repro = results.get("reproducibility")
    if result_repro is None:
        repro_score, repro_latency = 0.0, 0
    else:
        try:
            repro_score, repro_latency = result_repro
        except (TypeError, ValueError):
            repro_score, repro_latency = 0.0, 0

    result_review = results.get("reviewedness")
    if result_review is None:
        review_score, review_latency = 0.0, 0
    else:
        try:
            review_score, review_latency = result_review
        except (TypeError, ValueError):
            review_score, review_latency = 0.0, 0

    result_tree = results.get("treescore")
    if result_tree is None:
        tree_score, tree_latency = 0.0, 0
    else:
        try:
            tree_score, tree_latency = result_tree
        except (TypeError, ValueError):
            tree_score, tree_latency = 0.0, 0

    logger.info("Concurrent thread results unpacked")

    # Final net score calculation
    # Adjusted weights to accommodate new metrics (total = 1.0)
    net_score: float = (0.09 * license_score + 0.10 * ramp_score + 0.11 * net_size_score + 0.13 * data_quality_score + 0.10 * bus_score + 0.13 * dc_score + 0.10 * code_quality_score + 0.09 * perf_score + 0.05 * repro_score + 0.05 * max(review_score, 0) + 0.05 * tree_score)

    end = time.time()
    net_latency: int = int((end - start) * 1000)

    print_model_evaluation(
        model_info,
        size_scores, size_latency,
        license_score, license_latency,
        ramp_score, ramp_latency,
        bus_score, bus_latency,
        dc_score, dc_latency,
        data_quality_score, dq_latency,
        code_quality_score, cq_latency,
        perf_score, perf_latency,
        repro_score, repro_latency,
        review_score, review_latency,
        tree_score, tree_latency,
        net_score, net_latency
    )
    return ([net_size_score,
             license_score,
             ramp_score,
             bus_score,
             dc_score,
             data_quality_score,
             code_quality_score,
             perf_score,
             repro_score,
             review_score,
             tree_score])
