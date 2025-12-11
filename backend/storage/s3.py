"""
S3 storage utilities for artifact file storage.

Provides functions for uploading artifacts to S3 and generating pre-signed URLs
for secure downloads.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Get S3 client instance.

    Uses AWS_REGION environment variable if set, otherwise defaults to us-east-2.

    Returns:
        boto3.client('s3') if boto3 is available, None otherwise.

    Raises:
        RuntimeError: If boto3 is not available.
    """
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is not available. Install it with: pip install boto3")

    # Use AWS_REGION if set, otherwise default to us-east-2 (Ohio)
    region = os.getenv("AWS_REGION", "us-east-2")
    return boto3.client('s3', region_name=region)


def get_s3_bucket() -> str:
    """
    Get S3 bucket name from environment variable.

    Returns:
        S3 bucket name from S3_ARTIFACT_BUCKET environment variable.

    Raises:
        ValueError: If S3_ARTIFACT_BUCKET is not set.
    """
    bucket = os.getenv("S3_ARTIFACT_BUCKET")
    if not bucket:
        raise ValueError("S3_ARTIFACT_BUCKET environment variable is not set")
    return bucket


def get_s3_key(artifact_type: str, artifact_id: str) -> str:
    """
    Generate S3 key for an artifact.

    Args:
        artifact_type: Type of artifact (e.g., 'model', 'dataset', 'code').
        artifact_id: Unique artifact identifier.

    Returns:
        S3 key path: artifacts/{type}/{id}
    """
    return f"artifacts/{artifact_type}/{artifact_id}"


def upload_file_to_s3(
    file_path: str,
    artifact_type: str,
    artifact_id: str,
    content_type: str = 'application/octet-stream',
) -> bool:
    """
    Upload a file to S3.

    Args:
        file_path: Local path to the file to upload.
        artifact_type: Type of artifact (e.g., 'model', 'dataset', 'code').
        artifact_id: Unique artifact identifier.
        content_type: MIME type of the file (default: 'application/octet-stream').

    Returns:
        True if upload succeeded, False otherwise.

    Raises:
        RuntimeError: If boto3 is not available or S3 bucket is not configured.
    """
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is not available")

    try:
        s3_bucket = get_s3_bucket()
        s3_key = get_s3_key(artifact_type, artifact_id)
        s3_client = get_s3_client()

        logger.info(f"Uploading artifact {artifact_id} to S3: s3://{s3_bucket}/{s3_key}")

        s3_client.upload_file(
            file_path,
            s3_bucket,
            s3_key,
            ExtraArgs={'ContentType': content_type}
        )

        logger.info(f"Successfully uploaded artifact {artifact_id} to S3")
        return True

    except ValueError as e:
        logger.error(f"S3 bucket not configured: {e}")
        raise
    except (ClientError, BotoCoreError) as e:
        logger.error(f"S3 upload failed for artifact {artifact_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading artifact {artifact_id} to S3: {e}")
        return False


def file_exists_in_s3(artifact_type: str, artifact_id: str) -> bool:
    """
    Check if a file exists in S3.

    Args:
        artifact_type: Type of artifact (e.g., 'model', 'dataset', 'code').
        artifact_id: Unique artifact identifier.

    Returns:
        True if file exists, False otherwise.

    Raises:
        RuntimeError: If boto3 is not available or S3 bucket is not configured.
    """
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is not available")

    try:
        s3_bucket = get_s3_bucket()
        s3_key = get_s3_key(artifact_type, artifact_id)
        s3_client = get_s3_client()

        s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
        return True

    except ValueError as e:
        logger.error(f"S3 bucket not configured: {e}")
        raise
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404' or error_code == 'NoSuchKey':
            return False
        # Other S3 error - log and re-raise
        logger.error(f"S3 error checking artifact {artifact_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error checking artifact {artifact_id} in S3: {e}")
        raise


def generate_presigned_download_url(
    artifact_type: str,
    artifact_id: str,
    expiration: int = 900,
) -> Optional[str]:
    """
    Generate a pre-signed URL for downloading an artifact from S3.

    Args:
        artifact_type: Type of artifact (e.g., 'model', 'dataset', 'code').
        artifact_id: Unique artifact identifier.
        expiration: URL expiration time in seconds (default: 900 = 15 minutes).

    Returns:
        Pre-signed URL string, or None if generation failed.

    Raises:
        RuntimeError: If boto3 is not available or S3 bucket is not configured.
    """
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is not available")

    try:
        s3_bucket = get_s3_bucket()
        s3_key = get_s3_key(artifact_type, artifact_id)
        s3_client = get_s3_client()

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': s3_bucket,
                'Key': s3_key,
            },
            ExpiresIn=expiration
        )

        logger.info(f"Generated pre-signed URL for artifact {artifact_id} (expires in {expiration}s)")
        return presigned_url

    except ValueError as e:
        logger.error(f"S3 bucket not configured: {e}")
        raise
    except ClientError as e:
        logger.error(f"S3 error generating pre-signed URL for artifact {artifact_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating pre-signed URL for artifact {artifact_id}: {e}")
        return None
