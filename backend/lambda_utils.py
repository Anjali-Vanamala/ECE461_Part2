"""
Lambda-specific utilities for handling background tasks and async operations.

In Lambda, FastAPI's BackgroundTasks don't work because the execution context
ends when the handler returns. This module provides Lambda-compatible alternatives.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Callable, Any

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


def is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return os.getenv("COMPUTE_BACKEND") == "lambda" or bool(
        os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    )


def invoke_lambda_async(function_name: str, payload: dict[str, Any]) -> None:
    """
    Invoke a Lambda function asynchronously for background processing.
    
    Args:
        function_name: Name of the Lambda function to invoke
        payload: Payload to pass to the function
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available, cannot invoke Lambda function")
        return
    
    try:
        lambda_client = boto3.client("lambda", region_name=os.getenv("AWS_REGION", "us-east-2"))
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(payload)
        )
        logger.info(f"Successfully invoked Lambda function {function_name} asynchronously")
    except Exception as e:
        logger.error(f"Failed to invoke Lambda function {function_name}: {e}")
        raise


def run_in_background(task_func: Callable, *args, **kwargs) -> None:
    """
    Run a task in the background, using Lambda async invocation if in Lambda,
    otherwise using FastAPI BackgroundTasks.
    
    Args:
        task_func: Function to run in background
        *args: Positional arguments for task_func
        **kwargs: Keyword arguments for task_func
    """
    if is_lambda_environment():
        # In Lambda, we need to invoke a separate processing Lambda function
        # For now, we'll use a processing Lambda function name from environment
        processing_function = os.getenv(
            "LAMBDA_PROCESSING_FUNCTION",
            f"{os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'ece461-backend')}-processor"
        )
        
        # Serialize function call as payload
        # Note: This is a simplified approach. In production, you might want
        # to use a more robust task queue system (SQS, Step Functions, etc.)
        payload = {
            "task": task_func.__name__,
            "args": args,
            "kwargs": kwargs
        }
        
        try:
            invoke_lambda_async(processing_function, payload)
        except Exception as e:
            logger.error(f"Failed to invoke background task via Lambda: {e}")
            # Fallback: run synchronously (not ideal, but better than failing)
            logger.warning("Running background task synchronously as fallback")
            task_func(*args, **kwargs)
    else:
        # In ECS/other environments, use FastAPI BackgroundTasks
        # This will be handled by the route handler
        logger.debug("Not in Lambda environment, background task will be handled by FastAPI")
        # For non-Lambda, we still need to call it, but this function
        # is meant to be used with BackgroundTasks.add_task()
        task_func(*args, **kwargs)

