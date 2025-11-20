"""Storage abstraction layer.

This module provides a unified interface for storage backends.
Switch between in-memory and DynamoDB storage via the USE_DYNAMODB environment variable.
"""
import os

USE_DYNAMODB = os.getenv("USE_DYNAMODB", "0") == "1"

if USE_DYNAMODB:
    print(f"[Storage] Using DynamoDB backend (USE_DYNAMODB={os.getenv('USE_DYNAMODB')}, DDB_TABLE_NAME={os.getenv('DDB_TABLE_NAME')})")
    from . import dynamodb as storage  # noqa: F401
else:
    print(f"[Storage] Using in-memory backend (USE_DYNAMODB={os.getenv('USE_DYNAMODB', '0')})")
    from . import memory as storage  # type: ignore[no-redef]  # noqa: F401
