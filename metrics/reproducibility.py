"""
Reproducibility Metric Calculator for Models and Code Repositories.

Scores based on availability of example code in model files, GitHub repo,
or README.

Scoring:
    1.0 - Example code exists and appears valid
    0.0 - No example code found
"""

import ast
import re
import time
from typing import Any, Dict, Tuple

import logger

# Shared constants
EXAMPLE_KEYWORDS = ['example', 'demo', 'tutorial', 'quickstart',
                    'usage', 'sample']
EXAMPLE_EXTENSIONS = ['.py', '.ipynb', '.md']


def has_example_files(
    model_info: Dict[str, Any], code_info: Dict[str, Any]
) -> bool:
    """Check if example files exist in model or code repository."""
    # Check model repository files
    if model_info:
        siblings = model_info.get('siblings', [])
        for sibling in siblings:
            filename = sibling.get('rfilename', '').lower()
            if (any(kw in filename for kw in EXAMPLE_KEYWORDS) and
                    any(filename.endswith(ext) for ext in EXAMPLE_EXTENSIONS)):
                logger.debug(f"Found example file: {sibling.get('rfilename')}")
                return True

    # Check GitHub repo has examples directory or typical example files
    if code_info and code_info.get('full_name'):
        # Simple check - just see if repo metadata mentions examples
        description = code_info.get('description', '').lower()
        if any(kw in description for kw in EXAMPLE_KEYWORDS):
            logger.debug("Example mentioned in GitHub description")
            return True

    return False


def extract_and_validate_readme_code(readme: str) -> bool:
    """Extract Python code from README and validate syntax."""
    if not readme:
        return False

    # Find Python code blocks
    pattern = r'```python\s*(.*?)```'
    code_blocks = re.findall(pattern, readme, re.DOTALL | re.IGNORECASE)

    if not code_blocks:
        logger.debug("No Python code blocks found in README")
        return False

    logger.debug(f"Found {len(code_blocks)} code blocks in README")

    # Validate at least one code block has imports and valid syntax
    for code in code_blocks:
        # Check for imports (indicates real code, not pseudocode)
        if re.search(r'^\s*(import|from)\s+\w+', code, re.MULTILINE):
            try:
                # Remove leading whitespace from each line to fix
                # indentation issues
                lines = code.split('\n')
                dedented_lines = []
                for line in lines:
                    if line.strip():  # Only process non-empty lines
                        # Remove common leading whitespace
                        dedented_lines.append(line.lstrip())
                    else:
                        dedented_lines.append('')
                dedented_code = '\n'.join(dedented_lines)

                ast.parse(dedented_code)
                logger.debug("Found valid Python code with imports")
                return True
            except Exception:
                logger.debug("Code block has syntax errors")

    return False


def reproducibility(model_info: Dict[str, Any], code_info: Dict[str, Any],
                    model_readme: str) -> Tuple[float, int]:
    """
    Calculate reproducibility score based on example code availability
    and validity.

    Parameters
    ----------
    model_info : Dict
        Model information from Hugging Face API
    code_info : Dict
        GitHub repository information
    model_readme : str
        Model README content

    Returns
    -------
    Tuple[float, int]
        Reproducibility score (0.0-1.0) and latency in milliseconds
    """
    start = time.time()
    logger.info("Calculating reproducibility metric")

    score = 0.0

    try:
        # Check for example files in repositories
        has_files = has_example_files(model_info, code_info)

        # Check README for valid code examples
        readme_valid = extract_and_validate_readme_code(model_readme)

        # Score logic
        if has_files or readme_valid:
            score = 1.0  # Example code exists and appears valid
            logger.info("Example code found - score: 1.0")
        else:
            score = 0.0  # No examples found
            logger.info("No example code found - score: 0.0")

    except Exception as e:
        logger.info(f"Error calculating reproducibility: {e}")
        score = 0.0

    end = time.time()
    latency = int((end - start) * 1000)

    logger.info(f"Reproducibility score: {score}, latency: {latency}ms")

    return round(score, 2), latency
