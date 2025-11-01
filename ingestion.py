import os
import re
import sys
from urllib.parse import urlparse

import requests as rq

import logger
import metric_concurrent


def find_dataset(model_readme: str, seen_datasets: set) -> str:
    """
    If no dataset in input line, see if model was trained on
    a previously seen dataset.

    Parameters
    ----------
    model_readme : str
        Model README text

    Returns
    -------
    string
        The dataset link found, or None.
    """
    for dataset_url in seen_datasets:
        dataset = dataset_url.split("/")[-1].lower()
        if dataset in model_readme:
            logger.debug(f"Updated dataset url:{dataset_url}")
            return dataset_url
    return ""  # None found


def ingest(arg):
    """Main function to get & condition the user input url."""
    model_readme = ""
    dataset_readme = ""
    code_readme = ""
    model_info = {}
    code_info = {}

    logger.debug("\nBegin processing input")

    seen_datasets = set()

    input_lines = []
    if os.path.exists(arg):
        # Treat as a file
        with open(arg, "r", encoding="ascii") as input_file:
            input_lines = input_file.readlines()
    else:
        # Treat as a direct model URL (simulate ", ,model_url")
        input_lines = [f", ,{arg}\n"]

    # loop for reading each line:
    for line in input_lines:
        urls = [url.strip() for url in line.split(',')]

        # Handle cases with fewer than 3 URLs
        while len(urls) < 3:
            urls.append("")

        raw_code_url = urls[0]
        raw_dataset_url = urls[1]
        raw_model_url = urls[2]

        logger.info(f"Raw code url:{raw_code_url}\nRaw dataset url: {raw_dataset_url}\nRaw model url: {raw_model_url}")

        # ----- MODEL -----
        parsed_model = urlparse(raw_model_url)
        model_path = parsed_model.path.strip('/')
        parts = model_path.split("/")
        if "tree" in parts:
            tree_index = parts.index("tree")
            model_path = "/".join(parts[:tree_index])

        model_url = f'https://huggingface.co/api/models/{model_path}'
        try:
            api_response = rq.get(model_url)
            if api_response.status_code == 200:
                model_info = api_response.json()
        except Exception:
            model_info = {}

        model_rm_url = f"https://huggingface.co/{model_path}/raw/main/README.md"
        try:
            model_readme = rq.get(model_rm_url, timeout=50)
            if model_readme.status_code == 200:
                model_readme = model_readme.text.lower()
        except Exception:
            model_readme = ""

        # ----- DATASET -----
        parsed_dataset = urlparse(raw_dataset_url)
        dataset_path = parsed_dataset.path.strip('/')
        if raw_dataset_url:
            seen_datasets.add(raw_dataset_url)
        else:
            logger.debug("Dataset url not given. Search in previously seen.")
            raw_dataset_url = find_dataset(model_readme, seen_datasets)
            logger.debug(f"Found dataset url?:{raw_dataset_url}")

        dataset_url = f'https://huggingface.co/api/models/{dataset_path}'
        try:
            rq.get(dataset_url)
        except Exception as e:
            print(e)

        dataset_rm_url = f"https://huggingface.co/{dataset_path}/raw/main/README.md"
        try:
            dataset_readme = rq.get(dataset_rm_url, timeout=50)
            if dataset_readme.status_code == 200:
                dataset_readme = dataset_readme.text.lower()
        except Exception:
            dataset_readme = ""

        # ----- CODE -----
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
                code_readme = rq.get(f"{code_url}/readme", headers={'Accept': 'application/vnd.github.v3.raw'})
                if code_readme.status_code == 200:
                    code_readme = code_readme.text.lower()
            except Exception:
                code_readme = ""

        # ----- METRICS -----
        metrics = metric_concurrent.main(model_info, model_readme, raw_model_url, code_info, code_readme, raw_dataset_url)
        key = ["net_size_score",
               "license_score",
               "ramp_score",
               "bus_score",
               "dc_score",
               "data_quality_score",
               "code_quality_score",
               "perf_score",
               "repro_score",
               "review_score",
               "tree_score"]
        for i, value in enumerate(metrics):
            try:
                if float(value) < 0.5 and float(value) != -1.0:
                    print(f"Metric {key[i]}, {value} below threshold {0.5}")
                    logger.debug(f"Metric {key[i]}, {value} below threshold {0.5}")
                    return False
            except (ValueError, TypeError):
                logger.debug(f"Skipping non-numeric metric {value}")
                continue
        return True


if __name__ == "__main__":
    # Accept either a file or a single model URL
    arg = sys.argv[1]
    print(ingest(arg))
