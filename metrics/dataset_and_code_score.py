# If the dataset used for training and benchmarking is well documented,
#    along with any example code
import os
import re
import time
from typing import Optional, Tuple

import requests

import logger

"""
Use Purdue GenAI Studio to measure dataset documentation.

Parameters
----------
prompt : str
    Prompt with the dataset URL.

Returns
-------
string
    Response from LLM. Should be just a float in string format
"""


def extract_and_validate_readme_code(readme: str) -> bool:
    """Extract Python code from README and validate syntax."""
    if not readme:
        return False

    # Find Python code blocks
    pattern = r'```[^\n]*\n(.*?)```'
    code_blocks = re.findall(pattern, readme, re.DOTALL | re.IGNORECASE)

    if not code_blocks:
        logger.debug("No Python code blocks found in README")
        return False

    logger.debug(f"Found {len(code_blocks)} code blocks in README")
    return True


def query_genai_studio(prompt: str) -> str:
    # get api key from environment variable
    api_key = os.environ.get("GEN_AI_STUDIO_API_KEY")
    if not api_key:
        # When API key is not provided (e.g., local dev or CI without secrets),
        # avoid making an external network call and return a safe default score.
        logger.info("GEN_AI_STUDIO_API_KEY not set; returning default '0.0' response for GenAI Studio.")
        return "0.0"

    url = "https://genai.rcac.purdue.edu/api/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama3.1:latest",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        if response.status_code != 200:
            logger.info(f"GenAI Studio API returned status {response.status_code}; returning default '0.0'.")
            return "0.0"
        data = response.json()
        # OpenAI-style completion
        return data.get("choices", [])[0].get("message", {}).get("content", "0.0")
    except Exception as e:
        logger.info(f"Error calling GenAI Studio: {e}; returning default '0.0'.")
        return "0.0"


"""
Indicates if the dataset used for training and benchmarking
is well documented, along with any example code.

Parameters
----------
code_url :   string
    Example code url
dataset_url: string
    Dataset url

Returns
-------
tuple[float,float]
float
    Score in range 0 (bad) - 1 (good)
float
    latency of metric in seconds
"""


def dataset_and_code_score(
    code_info: dict | None,
    dataset_url: str,
    readme: str,
    *,
    dataset_name: Optional[str] = None
) -> Tuple[float, float]:
    # start latency timer
    start = time.time()
    logger.info("Calculating dataset_and_score metric")

    # Code, Dataset sources, uses, data collection and processing, bias
    # half of score is code exists
    # half of score is AI assessment of dataset documentation
    score = 0.0

    # Assume if no dataset or code link given, then it doesn't exist
    if extract_and_validate_readme_code(readme):
        score += 0.5

    # Give partial credit if a code repository was supplied
    if code_info:
        repo_url = code_info.get("html_url") if isinstance(code_info, dict) else None
        if repo_url:
            logger.debug(f"Detected linked code repository: {repo_url}")
            score += 0.3
        stars = code_info.get("stargazers_count", 0) if isinstance(code_info, dict) else 0
        if stars and stars > 0:
            score += 0.3

    # Backend should have already resolved the dataset URL before calling metrics
    effective_dataset_url = dataset_url

    if dataset_name and not effective_dataset_url:
        # Still provide a small bump if we at least know the dataset name
        score += 0.2

    # Use AI to parse Dataset url based on this Piazza post:
    #   "Yes you are suppose to use GenAI to help parse the information from the dataset link"
    if effective_dataset_url:
        score += .3  # add score for just having a dataset

        # now use AI since the dataset could be huggingface or not
        prompt = (f"Analyze the following dataset url to measure if the dataset used for training"
                  f"and benchmarking is well documented. This is a dataset used for a huggingface model."
                  f"If it is a widely used dataset such as bookcorpus you can assume it is very good."
                  f"Dataset URL:\n{effective_dataset_url}"
                  f"Return a score between 0 and 1. I am using this in code, so do not return ANYTHING"
                  f"but the float score. NO EXPLANATION. NOTHING BUT A FLOAT BETWEEN 0 AND 1.")
        valid_llm_output = False
        while valid_llm_output is False:
            llm_ouput = query_genai_studio(prompt)
            # Get float score from string
            try:
                llm_score = float(llm_ouput.strip())
                if (llm_score >= 0) and (llm_score <= 1):
                    valid_llm_output = True
                    score += llm_score * 0.4
                else:
                    logger.debug("Invalid llm output. Retrying.")
            except Exception:
                logger.debug("Invalid llm output. Retrying.")

    end = time.time()
    latency: float = end - start
    score = min(score, 1.0)
    return score, latency * 1000

# UNIT TEST


class Test_datasetandcodescore:
    def testbert(self):
        code_url = "https://github.com/google-research/bert"
        dataset_url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
        score, latency = dataset_and_code_score(code_url, dataset_url)
        assert abs(score - 1.0) < 1e-6
