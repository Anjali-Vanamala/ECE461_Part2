"""
Lambda-specific utilities.

In Lambda, FastAPI's BackgroundTasks don't work because the execution context
ends when the handler returns. Background processing is handled via threading
in the route handlers.
"""

from __future__ import annotations

import os


def is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return os.getenv("COMPUTE_BACKEND") == "lambda" or bool(
        os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    )
