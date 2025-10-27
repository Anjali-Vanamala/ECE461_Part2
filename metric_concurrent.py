from metrics.data_quality import data_quality
from metrics.code_quality import code_quality
from metrics.dataset_and_code_score import dataset_and_code_score
from metrics.performance_claims import performance_claims
from metrics.size import calculate_size_score
from metrics.bus_factor import bus_factor
from metrics.ramp_up_time import ramp_up_time
from metrics.license import get_license_score
from print_metrics import print_model_evaluation
import logger
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def main(model_info, model_readme, raw_model_url, code_info, code_readme, raw_dataset_url):
    start = time.time()
    logger.info("Begin processing metrics.")

    results = {}

    with ThreadPoolExecutor() as executor:
        future_to_metric = {
            executor.submit(data_quality, model_info, model_readme): "data_quality",
            executor.submit(code_quality, model_info, code_info, model_readme, code_readme): "code_quality",
            executor.submit(dataset_and_code_score, code_info, raw_dataset_url): "dc_score",
            executor.submit(performance_claims, raw_model_url): "performance_claims",
            executor.submit(calculate_size_score, raw_model_url): "size_score",
            executor.submit(get_license_score, raw_model_url): "license_score",
            executor.submit(bus_factor, model_info): "bus_factor",
            executor.submit(ramp_up_time, model_info): "ramp_up_time",
        }

        for future in as_completed(future_to_metric):
            metric_name = future_to_metric[future]
            try:
                results[metric_name] = future.result()
            except Exception as e:
                logger.debug(f"{metric_name} failed with error: {e}")
                results[metric_name] = None

    # Unpack the results
    data_quality_score, dq_latency = results["data_quality"]
    code_quality_score, cq_latency = results["code_quality"]
    dc_score, dc_latency = results["dc_score"]
    try:
        perf_score, perf_latency = results["performance_claims"]
    except (TypeError, KeyError):
        logger.debug("GenAI query failed to produce a result")
        perf_score, perf_latency = 0.0, 0
    size_scores, net_size_score, size_latency = results["size_score"]
    license_score, license_latency = results["license_score"]
    bus_score, bus_latency = results["bus_factor"]
    ramp_score, ramp_latency = results["ramp_up_time"]

    logger.info("Concurrent thread results unpacked")

    # Final net score calculation
    net_score = 0.1 * license_score + 0.11 * ramp_score + 0.12 * net_size_score + 0.15 * data_quality_score + 0.11 * bus_score + 0.2 * dc_score + 0.11 * code_quality_score + 0.1 * perf_score

    end = time.time()
    net_latency = int((end - start) * 1000)

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
        net_score, net_latency
    )
