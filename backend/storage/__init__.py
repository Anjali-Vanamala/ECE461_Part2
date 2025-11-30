import os
from typing import TYPE_CHECKING

# Check if we should use DynamoDB
if os.getenv("USE_DYNAMODB", "0") == "1":
    from backend.storage import dynamodb as memory  # type: ignore
else:
    from backend.storage import memory  # type: ignore
