import os

# Check if we should use DynamoDB
# Accept "1", "true", "True", "TRUE" as valid values
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "0").lower() in ("1", "true")

if USE_DYNAMODB:
    from backend.storage import dynamodb as memory  # type: ignore
    print("[Storage] Using DynamoDB backend")
else:
    from backend.storage import memory  # type: ignore
    print("[Storage] Using in-memory backend")

# Explicitly export the memory module
__all__ = ["memory"]