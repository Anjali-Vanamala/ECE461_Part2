"""
Lambda handler for FastAPI application.

This module provides the Lambda handler function that wraps the FastAPI app
using Mangum, enabling it to run on AWS Lambda with API Gateway.
"""

from __future__ import annotations

import os
import logging

# Set Lambda environment flag before importing app
os.environ["COMPUTE_BACKEND"] = "lambda"

try:
    from mangum import Mangum
except ImportError:
    raise ImportError(
        "mangum is required for Lambda deployment. Install with: pip install mangum"
    )

from backend.app import app

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Mangum adapter for FastAPI app
# lifespan="off" disables FastAPI lifespan events (not supported in Lambda)
# api_gateway_base_path="" allows API Gateway path configuration
handler = Mangum(
    app,
    lifespan="off",
    api_gateway_base_path="",
    log_level=logging.INFO
)

logger.info("Lambda handler initialized successfully")

