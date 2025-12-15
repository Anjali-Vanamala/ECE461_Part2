import os

# Check which storage backend to use
# Priority: STORAGE_BACKEND env var > USE_DYNAMODB (legacy) > default (memory)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "").lower()

# Legacy support: USE_DYNAMODB env var
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "0").lower() in ("1", "true")

if STORAGE_BACKEND == "dynamodb" or USE_DYNAMODB:
    from backend.storage import dynamodb as memory  # type: ignore
    print("[Storage] Using DynamoDB backend")
else:
    from backend.storage import memory  # type: ignore
    print("[Storage] Using in-memory backend")

# Explicitly export the memory module
__all__ = ["memory"]
