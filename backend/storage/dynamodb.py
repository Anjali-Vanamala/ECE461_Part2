from __future__ import annotations

import os
import uuid
from typing import Dict, Iterable, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from backend.models import (Artifact, ArtifactID, ArtifactMetadata,
                            ArtifactQuery, ArtifactType, ModelRating)
from backend.storage.records import CodeRecord, DatasetRecord, ModelRecord

# ---------------------------------------------------------------------------
# AWS / DynamoDB configuration
# ---------------------------------------------------------------------------

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "artifacts_metadata")

if not TABLE_NAME:
    raise RuntimeError("DDB_TABLE_NAME is not set in environment")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

# Primary key name
PK_NAME = "artifact_id"

# GSI for querying by type (if you add one later)
# For now, we'll use scan with filters

# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def generate_artifact_id() -> ArtifactID:
    return str(uuid.uuid4())


def _normalized(name: Optional[str]) -> Optional[str]:
    return name.strip().lower() if isinstance(name, str) else None


def _serialize_record(record: ModelRecord | DatasetRecord | CodeRecord) -> Dict:
    """Serialize a record to a DynamoDB-compatible dict."""
    result = {}

    # Serialize the artifact (Pydantic model)
    if hasattr(record.artifact, "model_dump"):
        result["artifact"] = record.artifact.model_dump()
    else:
        result["artifact"] = record.artifact.dict()

    # Add type-specific fields
    if isinstance(record, ModelRecord):
        result["artifact_type"] = ArtifactType.MODEL.value
        if record.rating:
            if hasattr(record.rating, "model_dump"):
                result["rating"] = record.rating.model_dump()
            else:
                result["rating"] = record.rating.dict()
        else:
            result["rating"] = None
        result["dataset_id"] = record.dataset_id
        result["dataset_name"] = record.dataset_name
        result["dataset_url"] = record.dataset_url
        result["code_id"] = record.code_id
        result["code_name"] = record.code_name
        result["code_url"] = record.code_url
    elif isinstance(record, DatasetRecord):
        result["artifact_type"] = ArtifactType.DATASET.value
    elif isinstance(record, CodeRecord):
        result["artifact_type"] = ArtifactType.CODE.value

    return result


def _deserialize_record(item: Dict) -> ModelRecord | DatasetRecord | CodeRecord:
    """Deserialize a DynamoDB item back to a record."""
    artifact_type_str = item.get("artifact_type")

    # Reconstruct Artifact from dict
    artifact_dict = item.get("artifact", {})
    artifact = Artifact(**artifact_dict)

    if artifact_type_str == ArtifactType.MODEL.value:
        rating_dict = item.get("rating")
        rating = ModelRating(**rating_dict) if rating_dict else None
        return ModelRecord(
            artifact=artifact,
            rating=rating,
            dataset_id=item.get("dataset_id"),
            dataset_name=item.get("dataset_name"),
            dataset_url=item.get("dataset_url"),
            code_id=item.get("code_id"),
            code_name=item.get("code_name"),
            code_url=item.get("code_url"),
        )
    elif artifact_type_str == ArtifactType.DATASET.value:
        return DatasetRecord(artifact=artifact)
    elif artifact_type_str == ArtifactType.CODE.value:
        return CodeRecord(artifact=artifact)
    else:
        raise ValueError(f"Unknown artifact type: {artifact_type_str}")


def _find_by_url(artifact_type: ArtifactType, url: str) -> Optional[ArtifactID]:
    """Find an artifact ID by URL and type."""
    # Scan with filter (for small tables, this is acceptable)
    try:
        response = table.scan(
            FilterExpression=Attr("artifact_type").eq(artifact_type.value)
        )
        for item in response.get("Items", []):
            artifact_dict = item.get("artifact", {})
            data_dict = artifact_dict.get("data", {})
            if data_dict.get("url") == url:
                return item[PK_NAME]

        # Handle pagination if needed
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(artifact_type.value),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                artifact_dict = item.get("artifact", {})
                data_dict = artifact_dict.get("data", {})
                if data_dict.get("url") == url:
                    return item[PK_NAME]
    except ClientError:
        pass

    return None


def _link_dataset_code(model_record: ModelRecord) -> None:
    """Link model to dataset and code by name matching."""
    dataset_name = _normalized(model_record.dataset_name)
    if model_record.dataset_id is None and dataset_name:
        # Scan for datasets
        try:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.DATASET.value)
            )
            for item in response.get("Items", []):
                artifact_dict = item.get("artifact", {})
                metadata_dict = artifact_dict.get("metadata", {})
                if _normalized(metadata_dict.get("name")) == dataset_name:
                    model_record.dataset_id = item[PK_NAME]
                    artifact_dict = item.get("artifact", {})
                    data_dict = artifact_dict.get("data", {})
                    model_record.dataset_url = data_dict.get("url")
                    # Update the model record in DynamoDB
                    _update_model_record(model_record)
                    break

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.DATASET.value),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    artifact_dict = item.get("artifact", {})
                    metadata_dict = artifact_dict.get("metadata", {})
                    if _normalized(metadata_dict.get("name")) == dataset_name:
                        model_record.dataset_id = item[PK_NAME]
                        artifact_dict = item.get("artifact", {})
                        data_dict = artifact_dict.get("data", {})
                        model_record.dataset_url = data_dict.get("url")
                        _update_model_record(model_record)
                        break
        except ClientError:
            pass

    code_name = _normalized(model_record.code_name)
    if model_record.code_id is None and code_name:
        # Scan for codes
        try:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.CODE.value)
            )
            for item in response.get("Items", []):
                artifact_dict = item.get("artifact", {})
                metadata_dict = artifact_dict.get("metadata", {})
                if _normalized(metadata_dict.get("name")) == code_name:
                    model_record.code_id = item[PK_NAME]
                    artifact_dict = item.get("artifact", {})
                    data_dict = artifact_dict.get("data", {})
                    model_record.code_url = data_dict.get("url")
                    # Update the model record in DynamoDB
                    _update_model_record(model_record)
                    break

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.CODE.value),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    artifact_dict = item.get("artifact", {})
                    metadata_dict = artifact_dict.get("metadata", {})
                    if _normalized(metadata_dict.get("name")) == code_name:
                        model_record.code_id = item[PK_NAME]
                        artifact_dict = item.get("artifact", {})
                        data_dict = artifact_dict.get("data", {})
                        model_record.code_url = data_dict.get("url")
                        _update_model_record(model_record)
                        break
        except ClientError:
            pass


def _update_model_record(model_record: ModelRecord) -> None:
    """Update a model record in DynamoDB."""
    item = _serialize_record(model_record)
    item[PK_NAME] = model_record.artifact.metadata.id
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# CRUD helpers (matching memory.py signatures)
# ---------------------------------------------------------------------------


def save_artifact(
    artifact: Artifact,
    *,
    rating: Optional[ModelRating] = None,
    dataset_name: Optional[str] = None,
    dataset_url: Optional[str] = None,
    code_name: Optional[str] = None,
    code_url: Optional[str] = None,
) -> Artifact:
    """Insert or update an artifact entry in DynamoDB."""
    artifact_id = artifact.metadata.id

    if artifact.metadata.type == ArtifactType.MODEL:
        # Get existing record if it exists
        existing_item = None
        try:
            response = table.get_item(Key={PK_NAME: artifact_id})
            existing_item = response.get("Item")
        except ClientError:
            pass

        if existing_item and existing_item.get("artifact_type") == ArtifactType.MODEL.value:
            # Update existing
            record = _deserialize_record(existing_item)
            if isinstance(record, ModelRecord):
                record.artifact = artifact
                record.rating = rating or record.rating
                record.dataset_name = dataset_name or record.dataset_name
                record.dataset_url = dataset_url or record.dataset_url
                record.code_name = code_name or record.code_name
                record.code_url = code_url or record.code_url
        else:
            # Create new
            record = ModelRecord(
                artifact=artifact,
                rating=rating,
                dataset_name=dataset_name,
                dataset_url=dataset_url,
                code_name=code_name,
                code_url=code_url,
            )

        _link_dataset_code(record)
        item = _serialize_record(record)
        item[PK_NAME] = artifact_id
        table.put_item(Item=item)

    elif artifact.metadata.type == ArtifactType.DATASET:
        record = DatasetRecord(artifact=artifact)
        item = _serialize_record(record)
        item[PK_NAME] = artifact_id
        table.put_item(Item=item)

        # Link to models that reference this dataset by name
        dataset_name_normalized = _normalized(artifact.metadata.name)
        try:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value)
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                if isinstance(record, ModelRecord):
                    if record.dataset_id is None and _normalized(record.dataset_name) == dataset_name_normalized:
                        record.dataset_id = artifact_id
                        record.dataset_url = artifact.data.url
                        _update_model_record(record)

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    record = _deserialize_record(item)
                    if isinstance(record, ModelRecord):
                        if record.dataset_id is None and _normalized(record.dataset_name) == dataset_name_normalized:
                            record.dataset_id = artifact_id
                            record.dataset_url = artifact.data.url
                            _update_model_record(record)
        except ClientError:
            pass

    elif artifact.metadata.type == ArtifactType.CODE:
        record = CodeRecord(artifact=artifact)
        item = _serialize_record(record)
        item[PK_NAME] = artifact_id
        table.put_item(Item=item)

        # Link to models that reference this code by name
        code_name_normalized = _normalized(artifact.metadata.name)
        try:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value)
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                if isinstance(record, ModelRecord):
                    if record.code_id is None and _normalized(record.code_name) == code_name_normalized:
                        record.code_id = artifact_id
                        record.code_url = artifact.data.url
                        _update_model_record(record)

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    record = _deserialize_record(item)
                    if isinstance(record, ModelRecord):
                        if record.code_id is None and _normalized(record.code_name) == code_name_normalized:
                            record.code_id = artifact_id
                            record.code_url = artifact.data.url
                            _update_model_record(record)
        except ClientError:
            pass
    else:
        raise ValueError(f"Unsupported artifact type: {artifact.metadata.type}")

    return artifact


def get_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> Optional[Artifact]:
    """Retrieve an artifact by type and ID."""
    try:
        response = table.get_item(Key={PK_NAME: artifact_id})
        item = response.get("Item")
        if not item:
            return None

        # Check type match
        if item.get("artifact_type") != artifact_type.value:
            return None

        record = _deserialize_record(item)
        return record.artifact
    except ClientError:
        return None


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    """Delete an artifact."""
    # First check if it exists and matches type
    try:
        response = table.get_item(Key={PK_NAME: artifact_id})
        item = response.get("Item")
        if not item:
            return False

        if item.get("artifact_type") != artifact_type.value:
            return False

        # Handle relationships
        if artifact_type == ArtifactType.DATASET:
            # Unlink from models
            try:
                scan_response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value)
                )
                for model_item in scan_response.get("Items", []):
                    record = _deserialize_record(model_item)
                    if isinstance(record, ModelRecord) and record.dataset_id == artifact_id:
                        record.dataset_id = None
                        record.dataset_url = None
                        _update_model_record(record)

                # Handle pagination
                while "LastEvaluatedKey" in scan_response:
                    scan_response = table.scan(
                        FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value),
                        ExclusiveStartKey=scan_response["LastEvaluatedKey"]
                    )
                    for model_item in scan_response.get("Items", []):
                        record = _deserialize_record(model_item)
                        if isinstance(record, ModelRecord) and record.dataset_id == artifact_id:
                            record.dataset_id = None
                            record.dataset_url = None
                            _update_model_record(record)
            except ClientError:
                pass
        elif artifact_type == ArtifactType.CODE:
            # Unlink from models
            try:
                scan_response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value)
                )
                for model_item in scan_response.get("Items", []):
                    record = _deserialize_record(model_item)
                    if isinstance(record, ModelRecord) and record.code_id == artifact_id:
                        record.code_id = None
                        record.code_url = None
                        _update_model_record(record)

                # Handle pagination
                while "LastEvaluatedKey" in scan_response:
                    scan_response = table.scan(
                        FilterExpression=Attr("artifact_type").eq(ArtifactType.MODEL.value),
                        ExclusiveStartKey=scan_response["LastEvaluatedKey"]
                    )
                    for model_item in scan_response.get("Items", []):
                        record = _deserialize_record(model_item)
                        if isinstance(record, ModelRecord) and record.code_id == artifact_id:
                            record.code_id = None
                            record.code_url = None
                            _update_model_record(record)
            except ClientError:
                pass

        # Delete the item
        table.delete_item(Key={PK_NAME: artifact_id})
        return True
    except ClientError:
        return False


def list_metadata(artifact_type: ArtifactType) -> List[ArtifactMetadata]:
    """List all metadata for a given artifact type."""
    results = []
    try:
        response = table.scan(
            FilterExpression=Attr("artifact_type").eq(artifact_type.value)
        )
        for item in response.get("Items", []):
            record = _deserialize_record(item)
            results.append(record.artifact.metadata)

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(artifact_type.value),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                results.append(record.artifact.metadata)
    except ClientError:
        pass

    return results


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    """Query artifacts by name and type."""
    results: Dict[str, ArtifactMetadata] = {}

    # Collect all types to query
    types_to_query = set()
    for query in queries:
        if query.types:
            types_to_query.update(query.types)
        else:
            types_to_query.update([ArtifactType.MODEL, ArtifactType.DATASET, ArtifactType.CODE])

    # Scan all relevant types
    try:
        for artifact_type in types_to_query:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(artifact_type.value)
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                metadata = record.artifact.metadata

                # Check against all queries
                for query in queries:
                    # Check if type matches
                    if query.types and artifact_type not in query.types:
                        continue

                    # Check name match (exact except "*")
                    if query.name == "*" or query.name.lower() == metadata.name.lower():
                        results[f"{metadata.type}:{metadata.id}"] = metadata
                        break

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    FilterExpression=Attr("artifact_type").eq(artifact_type.value),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                for item in response.get("Items", []):
                    record = _deserialize_record(item)
                    metadata = record.artifact.metadata

                    # Check against all queries
                    for query in queries:
                        # Check if type matches
                        if query.types and artifact_type not in query.types:
                            continue

                        # Check name match (exact except "*")
                        if query.name == "*" or query.name.lower() == metadata.name.lower():
                            results[f"{metadata.type}:{metadata.id}"] = metadata
                            break
    except ClientError:
        pass

    return list(results.values())


def reset() -> None:
    """Clear all artifacts from DynamoDB (for testing/dev only)."""
    try:
        # Scan all items
        response = table.scan(ProjectionExpression=PK_NAME)
        with table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(Key={PK_NAME: item[PK_NAME]})

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                ProjectionExpression=PK_NAME,
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            with table.batch_writer() as batch:
                for item in response.get("Items", []):
                    batch.delete_item(Key={PK_NAME: item[PK_NAME]})
    except ClientError:
        pass


# ---------------------------------------------------------------------------
# Additional helpers for registration workflow
# ---------------------------------------------------------------------------


def artifact_exists(artifact_type: ArtifactType, url: str) -> bool:
    """Check if an artifact with the given URL exists."""
    return _find_by_url(artifact_type, url) is not None


def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    """Save or update a model rating."""
    try:
        response = table.get_item(Key={PK_NAME: artifact_id})
        item = response.get("Item")
        if not item or item.get("artifact_type") != ArtifactType.MODEL.value:
            return

        record = _deserialize_record(item)
        if isinstance(record, ModelRecord):
            record.rating = rating
            _update_model_record(record)
    except ClientError:
        pass


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    """Get a model rating by artifact ID."""
    try:
        response = table.get_item(Key={PK_NAME: artifact_id})
        item = response.get("Item")
        if not item or item.get("artifact_type") != ArtifactType.MODEL.value:
            return None

        record = _deserialize_record(item)
        if isinstance(record, ModelRecord):
            return record.rating
    except ClientError:
        pass

    return None


def find_dataset_by_name(name: str) -> Optional[DatasetRecord]:
    """Find a dataset record by name."""
    normalized = _normalized(name)
    try:
        response = table.scan(
            FilterExpression=Attr("artifact_type").eq(ArtifactType.DATASET.value)
        )
        for item in response.get("Items", []):
            record = _deserialize_record(item)
            if isinstance(record, DatasetRecord):
                if _normalized(record.artifact.metadata.name) == normalized:
                    return record

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.DATASET.value),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                if isinstance(record, DatasetRecord):
                    if _normalized(record.artifact.metadata.name) == normalized:
                        return record
    except ClientError:
        pass

    return None


def find_code_by_name(name: str) -> Optional[CodeRecord]:
    """Find a code record by name."""
    normalized = _normalized(name)
    try:
        response = table.scan(
            FilterExpression=Attr("artifact_type").eq(ArtifactType.CODE.value)
        )
        for item in response.get("Items", []):
            record = _deserialize_record(item)
            if isinstance(record, CodeRecord):
                if _normalized(record.artifact.metadata.name) == normalized:
                    return record

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("artifact_type").eq(ArtifactType.CODE.value),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            for item in response.get("Items", []):
                record = _deserialize_record(item)
                if isinstance(record, CodeRecord):
                    if _normalized(record.artifact.metadata.name) == normalized:
                        return record
    except ClientError:
        pass

    return None
