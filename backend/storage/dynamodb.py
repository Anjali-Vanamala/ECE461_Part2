from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, cast

import boto3
from botocore.exceptions import ClientError

from backend.models import (Artifact, ArtifactID, ArtifactMetadata,
                            ArtifactQuery, ArtifactType, ModelRating)
from backend.storage.records import CodeRecord, DatasetRecord, ModelRecord

# DynamoDB setup
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "artifacts_metadata")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

print(f"[DynamoDB] Initialized - Table: {TABLE_NAME}, Region: {AWS_REGION}")


def generate_artifact_id() -> ArtifactID:
    return str(uuid.uuid4())


def _normalized(name: Optional[str]) -> Optional[str]:
    return name.strip().lower() if isinstance(name, str) else None


def _convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert all float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats_to_decimal(v) for v in obj]
    return obj


def _serialize_artifact(artifact: Artifact) -> Dict:
    """Convert Artifact to JSON-serializable dict."""
    return json.loads(artifact.model_dump_json())


def _deserialize_artifact(data: Dict) -> Artifact:
    """Convert dict to Artifact."""
    return Artifact(**data)


def _serialize_rating(rating: Optional[ModelRating]) -> Optional[Dict]:
    """Convert ModelRating to JSON-serializable dict."""
    if rating is None:
        return None
    return json.loads(rating.model_dump_json())


def _deserialize_rating(data: Optional[Dict]) -> Optional[ModelRating]:
    """Convert dict to ModelRating."""
    if data is None:
        return None
    return ModelRating(**data)


def _item_to_record(item: Dict) -> CodeRecord | DatasetRecord | ModelRecord:
    """Convert DynamoDB item to appropriate Record type."""
    artifact = _deserialize_artifact(item["artifact"])
    artifact_type = ArtifactType(item["artifact_type"])

    if artifact_type == ArtifactType.MODEL:
        return ModelRecord(
            artifact=artifact,
            rating=_deserialize_rating(item.get("rating")),
            dataset_id=item.get("dataset_id"),
            dataset_name=item.get("dataset_name"),
            dataset_url=item.get("dataset_url"),
            code_id=item.get("code_id"),
            code_name=item.get("code_name"),
            code_url=item.get("code_url"),
            processing_status=item.get("processing_status", "completed"),
        )
    elif artifact_type == ArtifactType.DATASET:
        return DatasetRecord(artifact=artifact)
    else:  # CODE
        return CodeRecord(artifact=artifact)


def save_artifact(
    artifact: Artifact,
    *,
    rating: Optional[ModelRating] = None,
    dataset_name: Optional[str] = None,
    dataset_url: Optional[str] = None,
    code_name: Optional[str] = None,
    code_url: Optional[str] = None,
    processing_status: Optional[str] = None,
) -> Artifact:
    """Insert or update an artifact entry in DynamoDB."""
    artifact_id = artifact.metadata.id
    artifact_type = artifact.metadata.type

    # Prepare base item
    item = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type.value,
        "artifact": _serialize_artifact(artifact),
        "name": artifact.metadata.name,
        "url": artifact.data.url,
    }
    # Only store normalized name if it's not empty
    normalized_name = _normalized(artifact.metadata.name)
    if normalized_name:
        item["name_normalized"] = normalized_name

    # Add model-specific fields
    if artifact_type == ArtifactType.MODEL:
        if rating is not None:
            rating_dict = _serialize_rating(rating)
            if rating_dict is not None:
                item["rating"] = rating_dict
        if dataset_name is not None:
            item["dataset_name"] = dataset_name
            normalized_dataset = _normalized(dataset_name)
            if normalized_dataset:  # Only store if not empty
                item["dataset_name_normalized"] = normalized_dataset
        if dataset_url is not None:
            item["dataset_url"] = dataset_url
        if code_name is not None:
            item["code_name"] = code_name
            normalized_code = _normalized(code_name)
            if normalized_code:  # Only store if not empty
                item["code_name_normalized"] = normalized_code
        if code_url is not None:
            item["code_url"] = code_url
        # Set processing_status: use provided value, or default to "completed"
        item["processing_status"] = processing_status if processing_status is not None else "completed"

    # Update dataset/code IDs for models that reference this
    if artifact_type == ArtifactType.DATASET:
        _update_models_with_dataset(artifact_id, artifact.metadata.name, artifact.data.url)
    elif artifact_type == ArtifactType.CODE:
        _update_models_with_code(artifact_id, artifact.metadata.name, artifact.data.url)

    try:
        # Convert all floats to Decimal for DynamoDB compatibility
        item = _convert_floats_to_decimal(item)
        table.put_item(Item=item)
        print(f"[DynamoDB] Saved artifact: {artifact_type.value}:{artifact_id}")
    except ClientError as e:
        print(f"[DynamoDB] Error saving artifact: {e}")
        raise

    # Try to link dataset/code by name if IDs not set (AFTER item is saved)
    if artifact_type == ArtifactType.MODEL:
        _link_dataset_code_by_name(artifact_id, dataset_name, code_name)

    return artifact


def _link_dataset_code_by_name(artifact_id: str, dataset_name: Optional[str], code_name: Optional[str]) -> None:
    """Update model record with dataset/code IDs if found by name."""
    if dataset_name:
        dataset_record = find_dataset_by_name(dataset_name)
        if dataset_record:
            _update_model_field(artifact_id, "dataset_id", dataset_record.artifact.metadata.id)
            _update_model_field(artifact_id, "dataset_url", dataset_record.artifact.data.url)

    if code_name:
        code_record = find_code_by_name(code_name)
        if code_record:
            _update_model_field(artifact_id, "code_id", code_record.artifact.metadata.id)
            _update_model_field(artifact_id, "code_url", code_record.artifact.data.url)


def _update_model_field(artifact_id: str, field_name: str, value: Optional[str]) -> None:
    """Update a single field in a model record."""
    try:
        update_expr = f"SET {field_name} = :val"
        table.update_item(
            Key={"artifact_id": artifact_id},
            UpdateExpression=update_expr,
            ConditionExpression="artifact_type = :type",
            ExpressionAttributeValues={":val": value, ":type": ArtifactType.MODEL.value},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            print(f"[DynamoDB] Error updating model field {field_name}: {e}")


def _update_models_with_dataset(dataset_id: str, dataset_name: str, dataset_url: str) -> None:
    """Update all models that reference this dataset by name."""
    normalized_name = _normalized(dataset_name) or ""
    try:
        response = table.scan(
            FilterExpression=(
                "artifact_type = :type "
                "AND dataset_name_normalized = :name "
                "AND attribute_not_exists(dataset_id)"
            ),
            ExpressionAttributeValues={":type": ArtifactType.MODEL.value, ":name": normalized_name},
        )
        for item in response.get("Items", []):
            table.update_item(
                Key={"artifact_id": item["artifact_id"]},
                UpdateExpression="SET dataset_id = :did, dataset_url = :url",
                ExpressionAttributeValues={":did": dataset_id, ":url": dataset_url},
            )
    except ClientError as e:
        print(f"[DynamoDB] Error updating models with dataset: {e}")


def _update_models_with_code(code_id: str, code_name: str, code_url: str) -> None:
    """Update all models that reference this code by name."""
    normalized_name = _normalized(code_name) or ""
    try:
        response = table.scan(
            FilterExpression=(
                "artifact_type = :type "
                "AND code_name_normalized = :name "
                "AND attribute_not_exists(code_id)"
            ),
            ExpressionAttributeValues={":type": ArtifactType.MODEL.value, ":name": normalized_name},
        )
        for item in response.get("Items", []):
            table.update_item(
                Key={"artifact_id": item["artifact_id"]},
                UpdateExpression="SET code_id = :cid, code_url = :url",
                ExpressionAttributeValues={":cid": code_id, ":url": code_url},
            )
    except ClientError as e:
        print(f"[DynamoDB] Error updating models with code: {e}")


def get_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> Optional[Artifact]:
    """Retrieve an artifact by type and ID."""
    try:
        response = table.get_item(Key={"artifact_id": artifact_id})
        if "Item" not in response:
            return None

        item = response["Item"]
        if item.get("artifact_type") != artifact_type.value:
            return None

        return _deserialize_artifact(item["artifact"])
    except ClientError as e:
        print(f"[DynamoDB] Error getting artifact: {e}")
        return None


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    """Delete an artifact."""
    # Check if exists and get it first
    artifact = get_artifact(artifact_type, artifact_id)
    if not artifact:
        return False

    # If deleting dataset/code, unlink from models
    if artifact_type == ArtifactType.DATASET:
        _unlink_dataset_from_models(artifact_id)
    elif artifact_type == ArtifactType.CODE:
        _unlink_code_from_models(artifact_id)

    try:
        table.delete_item(Key={"artifact_id": artifact_id})
        print(f"[DynamoDB] Deleted artifact: {artifact_type.value}:{artifact_id}")
        return True
    except ClientError as e:
        print(f"[DynamoDB] Error deleting artifact: {e}")
        return False


def _unlink_dataset_from_models(dataset_id: str) -> None:
    """Remove dataset_id and dataset_url from models that reference it."""
    try:
        response = table.scan(
            FilterExpression="artifact_type = :type AND dataset_id = :did",
            ExpressionAttributeValues={":type": ArtifactType.MODEL.value, ":did": dataset_id},
        )
        for item in response.get("Items", []):
            table.update_item(
                Key={"artifact_id": item["artifact_id"]},
                UpdateExpression="REMOVE dataset_id, dataset_url",
            )
    except ClientError as e:
        print(f"[DynamoDB] Error unlinking dataset from models: {e}")


def _unlink_code_from_models(code_id: str) -> None:
    """Remove code_id and code_url from models that reference it."""
    try:
        response = table.scan(
            FilterExpression="artifact_type = :type AND code_id = :cid",
            ExpressionAttributeValues={":type": ArtifactType.MODEL.value, ":cid": code_id},
        )
        for item in response.get("Items", []):
            table.update_item(
                Key={"artifact_id": item["artifact_id"]},
                UpdateExpression="REMOVE code_id, code_url",
            )
    except ClientError as e:
        print(f"[DynamoDB] Error unlinking code from models: {e}")


def list_metadata(artifact_type: ArtifactType) -> List[ArtifactMetadata]:
    """List all metadata for a given artifact type."""
    try:
        results = []
        response = table.scan(
            FilterExpression="artifact_type = :type",
            ExpressionAttributeValues={":type": artifact_type.value},
        )
        while True:
            for item in response.get("Items", []):
                artifact = _deserialize_artifact(item["artifact"])
                results.append(artifact.metadata)
            if "LastEvaluatedKey" not in response:
                break
            response = table.scan(
                FilterExpression="artifact_type = :type",
                ExpressionAttributeValues={":type": artifact_type.value},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
        return results
    except ClientError as e:
        print(f"[DynamoDB] Error listing metadata: {e}")
        return []


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    """Query artifacts by name and type."""
    results: Dict[str, ArtifactMetadata] = {}

    for query in queries:
        types = query.types or [ArtifactType.MODEL, ArtifactType.DATASET, ArtifactType.CODE]
        query_name_normalized = _normalized(query.name) if query.name != "*" else None

        for artifact_type in types:
            try:
                # Build filter expression
                if query_name_normalized:
                    filter_expr = "artifact_type = :type AND name_normalized = :name"
                    expr_values = {
                        ":type": artifact_type.value,
                        ":name": query_name_normalized,
                    }
                else:
                    filter_expr = "artifact_type = :type"
                    expr_values = {":type": artifact_type.value}

                # Scan with pagination
                response = table.scan(
                    FilterExpression=filter_expr,
                    ExpressionAttributeValues=expr_values,
                )
                while True:
                    for item in response.get("Items", []):
                        artifact = _deserialize_artifact(item["artifact"])
                        metadata = artifact.metadata
                        # Double-check name match (case-insensitive)
                        if query.name == "*" or query.name.lower() == metadata.name.lower():
                            results[f"{metadata.type}:{metadata.id}"] = metadata
                    if "LastEvaluatedKey" not in response:
                        break
                    response = table.scan(
                        FilterExpression=filter_expr,
                        ExpressionAttributeValues=expr_values,
                        ExclusiveStartKey=response["LastEvaluatedKey"],
                    )
            except ClientError as e:
                print(f"[DynamoDB] Error querying artifacts: {e}")

    return list(results.values())


def reset() -> None:
    """Delete all artifacts from the table."""
    try:
        # Scan all items and delete them (handle pagination)
        with table.batch_writer() as batch:
            response = table.scan(ProjectionExpression="artifact_id")
            while True:
                for item in response.get("Items", []):
                    batch.delete_item(Key={"artifact_id": item["artifact_id"]})
                if "LastEvaluatedKey" not in response:
                    break
                response = table.scan(
                    ProjectionExpression="artifact_id",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
        print("[DynamoDB] Reset: deleted all artifacts")
    except ClientError as e:
        print(f"[DynamoDB] Error resetting table: {e}")


def artifact_exists(artifact_type: ArtifactType, url: str) -> bool:
    """Check if an artifact with the given URL exists."""
    try:
        response = table.scan(
            FilterExpression="artifact_type = :type AND #u = :url",
            ExpressionAttributeNames={"#u": "url"},
            ExpressionAttributeValues={":type": artifact_type.value, ":url": url},
        )
        return len(response.get("Items", [])) > 0
    except ClientError as e:
        print(f"[DynamoDB] Error checking artifact existence: {e}")
        return False


def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    """Save or update a model rating."""
    try:
        rating_dict = _serialize_rating(rating)
        if rating_dict is not None:
            # Convert floats to Decimal for DynamoDB compatibility
            rating_dict = _convert_floats_to_decimal(rating_dict)
        table.update_item(
            Key={"artifact_id": artifact_id},
            UpdateExpression="SET rating = :rating",
            ConditionExpression="artifact_type = :type",
            ExpressionAttributeValues={
                ":rating": rating_dict,
                ":type": ArtifactType.MODEL.value,
            },
        )
        print(f"[DynamoDB] Saved rating for model: {artifact_id}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            print(f"[DynamoDB] Error saving model rating: {e}")


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    """Get the rating for a model."""
    try:
        response = table.get_item(Key={"artifact_id": artifact_id})
        if "Item" not in response:
            return None

        item = response["Item"]
        if item.get("artifact_type") != ArtifactType.MODEL.value:
            return None

        return _deserialize_rating(item.get("rating"))
    except ClientError as e:
        print(f"[DynamoDB] Error getting model rating: {e}")
        return None


def get_model_record(artifact_id: ArtifactID) -> Optional[ModelRecord]:
    """Get full model record with relationships (dataset_id, code_id)."""
    try:
        response = table.get_item(Key={"artifact_id": artifact_id})
        if "Item" not in response:
            return None

        item = response["Item"]
        if item.get("artifact_type") != ArtifactType.MODEL.value:
            return None

        # Type assertion: we've already verified it's a MODEL, so _item_to_record will return ModelRecord
        return cast(ModelRecord, _item_to_record(item))
    except ClientError as e:
        print(f"[DynamoDB] Error getting model record: {e}")
        return None


def get_processing_status(artifact_id: ArtifactID) -> Optional[str]:
    """Get the processing status of a model artifact."""
    try:
        response = table.get_item(Key={"artifact_id": artifact_id})
        if "Item" not in response:
            return None
        item = response["Item"]
        if item.get("artifact_type") != ArtifactType.MODEL.value:
            return None
        return item.get("processing_status", "completed")
    except ClientError as e:
        print(f"[DynamoDB] Error getting processing status: {e}")
        return None


def update_processing_status(artifact_id: ArtifactID, status: str) -> None:
    """Update the processing status of a model artifact."""
    try:
        table.update_item(
            Key={"artifact_id": artifact_id},
            UpdateExpression="SET processing_status = :status",
            ConditionExpression="artifact_type = :type",
            ExpressionAttributeValues={
                ":status": status,
                ":type": ArtifactType.MODEL.value,
            },
        )
        print(f"[DynamoDB] Updated processing status for model: {artifact_id}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            print(f"[DynamoDB] Error updating processing status: {e}")


def find_dataset_by_name(name: str) -> Optional[DatasetRecord]:
    """Find a dataset by normalized name."""
    normalized = _normalized(name) or ""
    try:
        response = table.scan(
            FilterExpression="artifact_type = :type AND name_normalized = :name",
            ExpressionAttributeValues={
                ":type": ArtifactType.DATASET.value,
                ":name": normalized,
            },
        )
        items = response.get("Items", [])
        if items:
            record = _item_to_record(items[0])
            if isinstance(record, DatasetRecord):
                return record
        return None
    except ClientError as e:
        print(f"[DynamoDB] Error finding dataset by name: {e}")
        return None


def find_code_by_name(name: str) -> Optional[CodeRecord]:
    """Find a code artifact by normalized name."""
    normalized = _normalized(name) or ""
    try:
        response = table.scan(
            FilterExpression="artifact_type = :type AND name_normalized = :name",
            ExpressionAttributeValues={
                ":type": ArtifactType.CODE.value,
                ":name": normalized,
            },
        )
        items = response.get("Items", [])
        if items:
            record = _item_to_record(items[0])
            if isinstance(record, CodeRecord):
                return record
        return None
    except ClientError as e:
        print(f"[DynamoDB] Error finding code by name: {e}")
        return None


# Helper function for regex search in artifacts.py
def _get_all_artifacts_for_regex() -> List[ArtifactMetadata]:
    """Get all artifacts for regex searching."""
    try:
        response = table.scan()
        results = []
        for item in response.get("Items", []):
            artifact = _deserialize_artifact(item["artifact"])
            results.append(artifact.metadata)
        return results
    except ClientError as e:
        print(f"[DynamoDB] Error getting all artifacts for regex: {e}")
        return []


# Expose for regex search compatibility - create a dict-like structure
class _StoreDict:
    """Dict-like wrapper for DynamoDB storage to match memory._TYPE_TO_STORE interface."""
    def __init__(self, artifact_type: ArtifactType):
        self.artifact_type = artifact_type

    def values(self):
        """Return records for this artifact type."""
        try:
            response = table.scan(
                FilterExpression="artifact_type = :type",
                ExpressionAttributeValues={":type": self.artifact_type.value},
            )
            while True:
                for item in response.get("Items", []):
                    yield _item_to_record(item)
                if "LastEvaluatedKey" not in response:
                    break
                response = table.scan(
                    FilterExpression="artifact_type = :type",
                    ExpressionAttributeValues={":type": self.artifact_type.value},
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
        except ClientError as e:
            print(f"[DynamoDB] Error getting values for {self.artifact_type}: {e}")


_TYPE_TO_STORE = {
    ArtifactType.MODEL: _StoreDict(ArtifactType.MODEL),
    ArtifactType.DATASET: _StoreDict(ArtifactType.DATASET),
    ArtifactType.CODE: _StoreDict(ArtifactType.CODE),
}
