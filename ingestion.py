import os
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests as rq

import logger
import metric_concurrent
from backend.models.artifact import ArtifactReference
from backend.storage import memory


def _derive_name_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    trimmed = url.rstrip("/").split("/")[-1]
    return trimmed or None


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


def _build_entry_list(
    arg: str,
    dataset_url: Optional[str],
    dataset_name: Optional[str],
    code_url: Optional[str],
    code_name: Optional[str]
) -> List[Dict[str, Optional[str]]]:
    """Normalize ingest inputs (file or direct URL) into a list of entries."""
    if os.path.exists(arg):
        with open(arg, "r", encoding="ascii") as input_file:
            lines = input_file.readlines()
        entries = []
        for line in lines:
            urls = [url.strip() for url in line.split(',')]
            while len(urls) < 3:
                urls.append("")
            entries.append(
                {
                    "code_url": urls[0] or None,
                    "dataset_url": urls[1] or None,
                    "model_url": urls[2] or None,
                    "dataset_name": None,
                    "code_name": None,
                }
            )
        return entries

    return [
        {
            "code_url": code_url,
            "dataset_url": dataset_url,
            "model_url": arg,
            "dataset_name": dataset_name,
            "code_name": code_name,
        }
    ]


def ingest(
    arg,
    *,
    dataset_url: str | None = None,
    dataset_name: str | None = None,
    code_url: str | None = None,
    code_name: str | None = None
):
    """Main function to get & condition the user input url."""
    model_readme = ""
    dataset_readme = ""
    code_readme = ""
    model_info = {}
    code_info = {}

    logger.debug("\nBegin processing input")

    seen_datasets = set()

    entries = _build_entry_list(arg, dataset_url, dataset_name, code_url, code_name)

    # loop for reading each entry:
    for entry in entries:
        raw_code_url = entry.get("code_url") or ""
        raw_dataset_url = entry.get("dataset_url") or ""
        raw_model_url = entry.get("model_url") or ""

        inferred_dataset_name = entry.get("dataset_name")
        inferred_code_name = entry.get("code_name")

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
        if inferred_dataset_name is None and raw_dataset_url:
            inferred_dataset_name = raw_dataset_url.split("/")[-1] or None
        parsed_dataset = urlparse(raw_dataset_url)
        dataset_path = parsed_dataset.path.strip('/')
        if not raw_dataset_url and inferred_dataset_name:
            existing_dataset = memory.find_dataset_by_name(inferred_dataset_name)
            if existing_dataset and existing_dataset.url:
                raw_dataset_url = existing_dataset.url

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
        if inferred_code_name is None and raw_code_url:
            inferred_code_name = raw_code_url.rstrip("/").split("/")[-1] or None
        if not raw_code_url and inferred_code_name:
            existing_code = memory.find_code_by_name(inferred_code_name)
            if existing_code and existing_code.url:
                raw_code_url = existing_code.url

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
        metrics = metric_concurrent.main(
            model_info,
            model_readme,
            raw_model_url,
            code_info,
            code_readme,
            raw_dataset_url,
            dataset_name=inferred_dataset_name,
            code_name=inferred_code_name
        )

        # Handle None return from metric_concurrent
        if metrics is None:
            logger.debug("metric_concurrent.main() returned None")
            return False

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

        # Check if metrics is iterable and has the expected length
        if not isinstance(metrics, (list, tuple)) or len(metrics) != len(key):
            logger.debug(f"Invalid metrics format: {metrics}")
            return False

        # Lower threshold for demo purposes (originally 0.5)
        # Set to 0.0 to accept any non-negative score
        threshold = 0.0

        for i, value in enumerate(metrics):
            try:
                if float(value) < threshold and float(value) != -1.0:
                    print(f"Metric {key[i]}, {value} below threshold {threshold}")
                    logger.debug(f"Metric {key[i]}, {value} below threshold {threshold}")
                    return False
            except (ValueError, TypeError):
                logger.debug(f"Skipping non-numeric metric {value}")
                continue

        # Record dataset/code hints for later reconciliation
        if raw_dataset_url or inferred_dataset_name:
            memory.upsert_dataset(
                ArtifactReference(
                    id=None,
                    name=inferred_dataset_name or _derive_name_from_url(raw_dataset_url),
                    type="dataset",
                    url=raw_dataset_url or None,
                )
            )
        if raw_code_url or inferred_code_name:
            memory.upsert_code(
                ArtifactReference(
                    id=None,
                    name=inferred_code_name or _derive_name_from_url(raw_code_url),
                    type="code",
                    url=raw_code_url or None,
                )
            )
        return True


if __name__ == "__main__":
    # Accept either a file or a single model URL
    arg = sys.argv[1]
    print(ingest(arg))
