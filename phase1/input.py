import os
import re
import sys
from urllib.parse import urlparse

import logger
import metric_concurrent
import requests as rq


def validate_environment() -> int:
    """Validate required environment variables at startup."""

    # Check GITHUB_TOKEN - simple validation
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token is not None:
        if not github_token or github_token.strip() == "" or github_token == "invalid":
            print("Error: Invalid GITHUB_TOKEN", file=sys.stderr)
            return 1

    # Check LOG_FILE - simple validation (don't create files)
    log_file = os.getenv("LOG_FILE")
    if log_file is not None:
        if not os.path.exists(log_file):
            print(f"Error: Log file does not exist: {log_file}", file=sys.stderr)
            return 1

    # Check LOG_LEVEL
    log_level = os.getenv("LOG_LEVEL")
    if log_level is not None:
        try:
            level = int(log_level)
            if level < 0 or level > 2:
                print(f"Error: LOG_LEVEL must be 0, 1, or 2, got: {level}", file=sys.stderr)
                return 1
        except ValueError:
            print(f"Error: LOG_LEVEL must be an integer, got: {log_level}", file=sys.stderr)
            return 1

    return 0


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


def main():
    """Main function to get & condition the user input url."""
    # Validate environment variables first
    if validate_environment() != 0:
        sys.exit(1)

    model_readme = ""
    dataset_readme = ""
    code_readme = ""
    model_info = {}
    code_info = {}

    logger.debug("\nBegin processing input")
    url_file = sys.argv[1]
    seen_datasets = set()
    with open(url_file, "r", encoding="ascii") as input:
        # loop for reading each line:
        for line in input:
            urls = [url.strip() for url in line.split(',')]

            raw_code_url = urls[0]
            raw_dataset_url = urls[1]
            raw_model_url = urls[2]

            logger.info(f"Raw code url:{raw_code_url}\nRaw dataset url: {raw_dataset_url}\nRaw model url: {raw_model_url}")

            # ----- MODEL -----
            # Parse model path
            parsed_model = urlparse(raw_model_url)
            model_path = parsed_model.path.strip('/')
            parts = model_path.split("/")
            if "tree" in parts:
                tree_index = parts.index("tree")
                model_path = "/".join(parts[:tree_index])
            # Model url for API
            model_url = f'https://huggingface.co/api/models/{model_path}'
            try:
                api_response = rq.get(model_url)
                if api_response.status_code == 200:
                    model_info = api_response.json()  # api info for dataset
            except Exception:
                model_info = {}
            # Model readme
            model_rm_url = f"https://huggingface.co/{model_path}/raw/main/README.md"
            try:
                model_readme = rq.get(model_rm_url, timeout=50)
                if model_readme.status_code == 200:
                    model_readme = model_readme.text.lower()
            except Exception:
                model_readme = ""
            # -----------------

            # ----- DATASET -----
            # Parse dataset path
            parsed_dataset = urlparse(raw_dataset_url)
            dataset_path = parsed_dataset.path.strip('/')
            # handle if no datast URL given
            if raw_dataset_url:
                seen_datasets.add(raw_dataset_url)
            else:
                logger.debug("Dataset url not given. Search in previously seen.")
                raw_dataset_url = find_dataset(model_readme, seen_datasets)
                logger.debug(f"Found dataset url?:{raw_dataset_url}")

            # dataset readme - DELETE IF NOT USED
            dataset_url = f'https://huggingface.co/api/models/{dataset_path}'
            try:
                api_response = rq.get(dataset_url)
            except Exception as e:
                print(e)
            dataset_rm_url = f"https://huggingface.co/{dataset_path}/raw/main/README.md"
            try:
                dataset_readme = rq.get(dataset_rm_url, timeout=50)
                if dataset_readme.status_code == 200:
                    dataset_readme = dataset_readme.text.lower()
            except Exception:
                dataset_readme = ""
            # -------------------

            # ----- CODE -----
            # DELETE IF NOT USED
            match = re.search(r'github\.com/([^/]+)/([^/]+)', raw_code_url)
            if match:
                owner, repo = match.groups()
                repo = repo.replace('.git', '')
                code_url = f"https://api.github.com/repos/{owner}/{repo}"  # api url for code

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
            # --------------------

            # Analyze metrics
            metric_concurrent.main(model_info, model_readme, raw_model_url, code_info, code_readme, raw_dataset_url)


if __name__ == "__main__":
    main()
