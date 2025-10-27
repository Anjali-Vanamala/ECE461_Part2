'''
pip install huggingface_hub
'''
import logger

'''
Completeness
comment out once completed after readme info can be verified
pip3 install datasets

Try #1: Check a list of completeness keywords in the card_data and readme, not an ideal indicator of completeness
Try #2: Use pandas isnull to check if there's a missing value in the dataset
'''


def complete_checker(api_info, readme):

    logger.debug("Starting completeness check")

    card_data = api_info.get('cardData', {})

    # Expanded completeness indicators - more flexible matching
    complete_kw = {
        # Essential metadata completeness
        'license': ['license', 'apache', 'mit', 'bsd', 'cc', 'gpl'],
        'description': ['description', 'model', 'pretrained', 'fine-tuned'],
        'use': ['use', 'usage', 'intended', 'downstream', 'task'],
        'limitation': ['limitation', 'bias', 'constraint', 'caution', 'note'],
        'tags': ['tags', 'tag'],
        'citation': ['citation', 'cite', 'bibtex', 'paper', 'arxiv', 'reference'],
        'source': ['source', 'data', 'dataset', 'corpus', 'training'],
        'language': ['language', 'english', 'multilingual', 'en'],
        'datasets': ['wikipedia', 'bookcorpus']
    }

    score = 0
    for category, keywords in complete_kw.items():
        # Check in card_data first (exact match)
        if category in card_data:
            score += 1
            continue

        # Check for any of the keywords in readme (flexible matching)
        if any(keyword.lower() in readme.lower() for keyword in keywords):
            score += 1

    logger.info(f"Completeness keywords found: {score}")

    # More generous scoring for well-documented models
    if score >= 6:
        return 1.0
    elif score >= 4:
        return 0.7
    elif score >= 2:
        return 0.5
    else:
        return 0.1


def correct_checker(readme: str):
    import re

    logger.debug("Starting correctness check")

    if not readme:
        return 0.0

    # Expanded accuracy patterns
    acc_pattern = [
        r'type:\s*accuracy\s*value:\s*([\d.]+)',
        r'accuracy:\s*([\d.]+)',
        r'"accuracy":\s*([\d.]+)',
        # Look for evaluation results, scores, performance metrics
        r'score[:\s]+([\d.]+)',
        r'achieves[^0-9]*([\d.]+)',
        r'results?[:\s][^0-9]*([\d.]+)',
        r'performance[^0-9]*([\d.]+)',
        r'(\d+\.\d+)(?:\s*%?)',  # Any decimal number (be careful with this)
    ]

    # Also look for evaluation tables/sections
    evaluation_indicators = [
        'evaluation', 'results', 'performance', 'benchmark', 'glue',
        'accuracy', 'f1', 'score', 'metric'
    ]

    eval_mentions = sum(1 for indicator in evaluation_indicators if indicator.lower() in readme.lower())
    logger.info(f"eval ments found: {eval_mentions}")

    for pattern in acc_pattern:
        match = re.search(pattern, readme, re.IGNORECASE)
        if match:
            try:
                accuracy_val = float(match.group(1))
                logger.info(f"accuracy: {accuracy_val}")
                if 0 <= accuracy_val <= 1:  # Valid probability
                    return accuracy_val
                elif accuracy_val <= 100:  # Percentage
                    return 1.0
            except Exception:
                continue

    # If no specific accuracy but has evaluation section, give partial credit
    if eval_mentions >= 3:
        logger.info(f"Completeness keywords found: {eval_mentions}")
        return 0.7  # Give credit for thorough evaluation discussion

    logger.info("No accuracy information found")

    return 0.0


'''
Try #1: treats more data labels = more coverage
Coverage calculator -> readme content search to analyze coverage

'''


def coverage_checker(api_info: str, readme: str):

    # Following list of words are used as a filter on the readme file. This lis it curated by
    # Claude Sonnet 4 with the following prompts:
    '''
    "Give me a list of words that can be used on Hugging Face model readme content to check if the model
    can be credited for data coverage. remember that these words will be used as a filter to score the data quality
    of the model, so try to have a comprehensive list." and
    "not geographic coverage, we are testing whether the data is diverse on samples
    so it represents the general population of a specific purpose well."
    '''
    logger.debug("Starting coverage check")

    checked_words = ['diverse', 'diversity', 'varied', 'variety', 'various', 'different',
                     'heterogeneous', 'mixed', 'multiple', 'range', 'spectrum',

                     # Representativeness
                     'representative', 'represents', 'representative sample', 'cross-section',
                     'reflects', 'mirrors', 'captures', 'encompasses', 'covers',
                     'comprehensive', 'extensive', 'broad', 'wide', 'spanning',

                     # Balance and distribution
                     'balanced', 'well-balanced', 'evenly distributed', 'uniform',
                     'stratified', 'proportional', 'equal representation', 'fair distribution',
                     'well-distributed', 'equally represented', 'balanced across']

    coverage_count = sum(1 for word in checked_words if word in readme)

    # Simple scoring based on coverage word frequency
    if coverage_count >= 10:
        return 1.0  # Highly descriptive of coverage
    elif coverage_count >= 5:
        return 0.7  # Good coverage description
    elif coverage_count >= 1:
        return 0.5  # Some coverage mentioned
    else:
        return 0.3  # No clear coverage description


'''
Relevance calculator

Parameters
----------
api_info: str
    api info in json format, extracted from user input post-parsing

Returns
-------
relevance_score : int
    parameter that stores the calculated relevance information
        0.1 if the model 0-90 days old
        0.06 if the model 90-180 days old
        0.03 if the model 180-360 days old
        0.01 if the model +360 days old

'''


def relevance_checker(api_info: str):

    from datetime import date
    from dateutil import parser

    logger.debug("Starting relevance check")

    today = date.today()  # todays date

    try:
        date_creation = api_info['createdAt']  # extract creation date from json, returns date & time format
        date_creation = parser.parse(date_creation)  # format the date/time info, make it easy to extract date
        date_creation = date_creation.date()  # extract date wo the time/time zone

        days_passed = (today - date_creation).days  # get number of days passed in int

        # categorize relevance based on the number of days passed
        # might need to change the thresholds depending on the testcases fed, relevance of 1 year might be too ambitious
        # update: changed
        if days_passed > 2500:
            relevance_score = 0.2
        elif days_passed > 1500:
            relevance_score = 0.4
        elif days_passed > 750:
            relevance_score = 0.7
        else:
            relevance_score = 1.0

        return relevance_score

    except KeyError:
        logger.info("Error: 'createdAt' field not found in API info")
        return 0.0
    except Exception as e:
        logger.info(f"Error parsing creation date: {e}")
        return 0.0


'''
Finalizes data_quality calcs

Parameters
----------
api_info: str
    api info in json format, extracted from user input post-parsing, passed in from master_scoring
readme: str
    readme passed in from master_scoring

Returns
-------
data_quality_score : int
    calculated with the following metrics:
        - completeness -> checks list of completeness keywords in the card_data and readme, weight: 0.3x
        - correctness -> extracts the accuracy tag & its value from readmes, weight: 0.2x (since most readmes dont have it)
        - coverage -> readme filter words count to analyze coverage, weight: 0.2x
        - relevance -> checks the # of days since the model created, weight: 0.3x
'''


def data_quality(api_info, readme):
    import time
    start = time.time()
    logger.info("Calculating data_quality metric")

    data_quality_score = 0.0

    complete = complete_checker(api_info, readme)
    correct = correct_checker(readme)
    coverage = coverage_checker(api_info, readme)
    relevance = relevance_checker(api_info)

    data_quality_score = (complete * 0.3 + correct * 0.2 + coverage * 0.2 + relevance * 0.3)

    end = time.time()
    latency = end - start

    return data_quality_score, latency
