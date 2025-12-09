import os
from typing import Optional, Iterable, List
import boto3
from boto3.dynamodb.conditions import Key

from backend.models import (
    Artifact, ArtifactID, ArtifactMetadata, ArtifactQuery,
    ArtifactType, ModelRating
)

# Import your existing in-memory implementation
import backend.storage.memory as memory


# ---------------------------------------------------------------------------
# Environment flag switch
# ---------------------------------------------------------------------------

USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# DynamoDB setup
# ---------------------------------------------------------------------------

if USE_DYNAMODB:
    dynamodb = boto3.resource("dynamodb")
    table_models = dynamodb.Table("Models")
    table_datasets = dynamodb.Table("Datasets")
    table_code = dynamodb.Table("Code")


# ---------------------------------------------------------------------------
# Helpers: conversion utilities
# ---------------------------------------------------------------------------

def _artifact_to_item(artifact: Artifact, **extra_fields):
    """Convert artifact into a dict suitable for DynamoDB."""
    item = {
        "id": artifact.metadata.id,
        "type": artifact.metadata.type.value,
        "name": artifact.metadata.name,
        "url": artifact.data.url,
        "metadata": artifact.metadata.model_dump(),
        "data": artifact.data.model_dump(),
    }
    for k, v in extra_fields.items():
        if v is not None:
            item[k] = v
    return item


def _item_to_artifact(item) -> Artifact:
    """Convert a DynamoDB record back into an Artifact."""
    metadata = ArtifactMetadata(**item["metadata"])
    data = item["data"]
    return Artifact(metadata=metadata, data=data)


# ---------------------------------------------------------------------------
# Unified storage API (DynamoDB or Memory)
# ---------------------------------------------------------------------------

def save_artifact(
    artifact: Artifact,
    *,
    rating: Optional[ModelRating] = None,
    license: Optional[str] = None,
    dataset_name: Optional[str] = None,
    dataset_url: Optional[str] = None,
    code_name: Optional[str] = None,
    code_url: Optional[str] = None,
    processing_status: Optional[str] = None,
) -> Artifact:
    if not USE_DYNAMODB:
        return memory.save_artifact(
            artifact,
            rating=rating,
            license=license,
            dataset_name=dataset_name,
            dataset_url=dataset_url,
            code_name=code_name,
            code_url=code_url,
            processing_status=processing_status,
        )

    # DynamoDB mode
    t = artifact.metadata.type
    item = _artifact_to_item(
        artifact,
        rating=rating,
        license=license,
        dataset_name=dataset_name,
        dataset_url=dataset_url,
        code_name=code_name,
        code_url=code_url,
        processing_status=processing_status or "completed",
    )

    if t == ArtifactType.MODEL:
        table_models.put_item(Item=item)
    elif t == ArtifactType.DATASET:
        table_datasets.put_item(Item=item)
    elif t == ArtifactType.CODE:
        table_code.put_item(Item=item)

    return artifact


def get_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> Optional[Artifact]:
    if not USE_DYNAMODB:
        return memory.get_artifact(artifact_type, artifact_id)

    table = {
        ArtifactType.MODEL: table_models,
        ArtifactType.DATASET: table_datasets,
        ArtifactType.CODE: table_code,
    }[artifact_type]

    resp = table.get_item(Key={"id": artifact_id})
    if "Item" not in resp:
        return None

    return _item_to_artifact(resp["Item"])


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    if not USE_DYNAMODB:
        return memory.delete_artifact(artifact_type, artifact_id)

    table = {
        ArtifactType.MODEL: table_models,
        ArtifactType.DATASET: table_datasets,
        ArtifactType.CODE: table_code,
    }[artifact_type]

    table.delete_item(Key={"id": artifact_id})
    return True


def list_metadata(artifact_type: ArtifactType) -> List[ArtifactMetadata]:
    if not USE_DYNAMODB:
        return memory.list_metadata(artifact_type)

    table = {
        ArtifactType.MODEL: table_models,
        ArtifactType.DATASET: table_datasets,
        ArtifactType.CODE: table_code,
    }[artifact_type]

    resp = table.scan()
    return [ArtifactMetadata(**item["metadata"]) for item in resp.get("Items", [])]


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    if not USE_DYNAMODB:
        return memory.query_artifacts(queries)

    results = {}

    # DynamoDB side is simplified — assumes scanning
    for query in queries:
        for artifact_type in query.types or ArtifactType:
            table = {
                ArtifactType.MODEL: table_models,
                ArtifactType.DATASET: table_datasets,
                ArtifactType.CODE: table_code,
            }[artifact_type]

            resp = table.scan()
            for item in resp.get("Items", []):
                name = item["metadata"]["name"]
                if query.name == "*" or query.name.lower() == name.lower():
                    meta = ArtifactMetadata(**item["metadata"])
                    results[f"{meta.type}:{meta.id}"] = meta

    return list(results.values())


def reset() -> None:
    if not USE_DYNAMODB:
        return memory.reset()
    # In DynamoDB mode, do nothing or optionally wipe tables
    pass


# ---------------------------------------------------------------------------
# Additional helpers (ratings, licenses)
# ---------------------------------------------------------------------------

def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    if not USE_DYNAMODB:
        return memory.save_model_rating(artifact_id, rating)

    table_models.update_item(
        Key={"id": artifact_id},
        UpdateExpression="SET rating = :r",
        ExpressionAttributeValues={":r": rating},
    )


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    if not USE_DYNAMODB:
        return memory.get_model_rating(artifact_id)

    resp = table_models.get_item(Key={"id": artifact_id})
    return resp.get("Item", {}).get("rating")


def save_model_license(artifact_id: ArtifactID, license: str) -> None:
    if not USE_DYNAMODB:
        return memory.save_model_license(artifact_id, license)

    table_models.update_item(
        Key={"id": artifact_id},
        UpdateExpression="SET license = :l",
        ExpressionAttributeValues={":l": license},
    )


def get_model_license(artifact_id: ArtifactID) -> Optional[str]:
    if not USE_DYNAMODB:
        return memory.get_model_license(artifact_id)

    resp = table_models.get_item(Key={"id": artifact_id})
    return resp.get("Item", {}).get("license")


def get_processing_status(artifact_id: ArtifactID) -> Optional[str]:
    if not USE_DYNAMODB:
        return memory.get_processing_status(artifact_id)

    resp = table_models.get_item(Key={"id": artifact_id})
    return resp.get("Item", {}).get("processing_status")


def update_processing_status(artifact_id: ArtifactID, status: str) -> None:
    if not USE_DYNAMODB:
        return memory.update_processing_status(artifact_id, status)

    table_models.update_item(
        Key={"id": artifact_id},
        UpdateExpression="SET processing_status = :s",
        ExpressionAttributeValues={":s": status},
    )
