import os

# Check if we should use DynamoDB
if os.getenv("USE_DYNAMODB", "0") == "1":
    from backend.storage import dynamodb as memory
else:
    from backend.storage import memory

