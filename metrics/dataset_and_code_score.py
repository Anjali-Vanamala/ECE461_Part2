# If the dataset used for training and benchmarking is well documented,
#    along with any example code
import os
import sys
import time
from typing import Tuple

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


def query_genai_studio(prompt: str) -> str:
    # get api key from environment variable
    api_key = os.environ.get("GEN_AI_STUDIO_API_KEY")
    if not api_key:
        logger.info("Error: GEN_AI_STUDIO_API_KEY environment variable not found")
        sys.exit(1)

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

    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"GenAI Studio API error: {response.status_code}, {response.text}")

    data = response.json()
    # OpenAI-style completion
    return data["choices"][0]["message"]["content"]


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


def dataset_and_code_score(code_url: str, dataset_url: str) -> Tuple[float, float]:
    # start latency timer
    start = time.time()
    logger.info("Calculating dataset_and_score metric")

    # Code, Dataset sources, uses, data collection and processing, bias
    # half of score is code exists
    # half of score is AI assessment of dataset documentation
    score = 0.0

    # Assume if no dataset or code link given, then it doesn't exist
    if code_url:
        score += 0.5

    # Use AI to parse Dataset url based on this Piazza post:
    #   "Yes you are suppose to use GenAI to help parse the information from the dataset link"
    if dataset_url:
        score += .1  # add score for just having a dataset

        # now use AI since the dataset could be huggingface or not
        prompt = (f"Analyze the following dataset url to measure if the dataset used for training"
                  f"and benchmarking is well documented. This is a dataset used for a huggingface model."
                  f"If it is a widely used dataset such as bookcorpus you can assume it is very good."
                  f"Dataset URL:\n{dataset_url}"
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
    return score, latency * 1000

# UNIT TEST


class Test_datasetandcodescore:
    def testbert(self):
        code_url = "https://github.com/google-research/bert"
        dataset_url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
        score, latency = dataset_and_code_score(code_url, dataset_url)
        assert abs(score - 1.0) < 1e-6
