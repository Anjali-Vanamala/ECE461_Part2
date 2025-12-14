"""
RDS PostgreSQL storage backend for artifacts.

Uses SQLAlchemy ORM to interact with PostgreSQL database.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Dict, Iterable, List, Optional

try:
    from sqlalchemy import (
        JSON,
        String,
        Text,
        create_engine,
        Column,
        Index,
        select,
        update,
        delete,
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None
    Session = None

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from backend.models import (
    Artifact,
    ArtifactID,
    ArtifactMetadata,
    ArtifactQuery,
    ArtifactType,
    ModelRating,
)
from backend.storage.records import CodeRecord, DatasetRecord, ModelRecord

# Database configuration
RDS_ENDPOINT = os.getenv("RDS_ENDPOINT")
RDS_DB_NAME = os.getenv("RDS_DB_NAME", "artifacts_db")
RDS_USERNAME = os.getenv("RDS_USERNAME", "postgres")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_PORT = os.getenv("RDS_PORT", "5432")

if not SQLALCHEMY_AVAILABLE:
    raise ImportError("SQLAlchemy is required for RDS backend. Install with: pip install sqlalchemy")

if not PSYCOPG2_AVAILABLE:
    raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")

# SQLAlchemy setup
Base = declarative_base()


class ArtifactModel(Base):
    """SQLAlchemy model for artifacts table."""
    __tablename__ = "artifacts"

    artifact_id = Column(String(255), primary_key=True)
    artifact_type = Column(String(50), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    name_normalized = Column(String(500), index=True)
    url = Column(String(2000), nullable=False, index=True)
    artifact_data = Column(JSON, nullable=False)  # Full artifact JSON
    rating = Column(JSON, nullable=True)  # Model rating JSON
    license = Column(String(200), nullable=True)
    dataset_id = Column(String(255), nullable=True, index=True)
    dataset_name = Column(String(500), nullable=True)
    dataset_name_normalized = Column(String(500), index=True)
    dataset_url = Column(String(2000), nullable=True)
    code_id = Column(String(255), nullable=True, index=True)
    code_name = Column(String(500), nullable=True)
    code_name_normalized = Column(String(500), index=True)
    code_url = Column(String(2000), nullable=True)
    processing_status = Column(String(50), default="completed")

    __table_args__ = (
        Index("idx_artifact_type_name", "artifact_type", "name_normalized"),
        Index("idx_artifact_type_url", "artifact_type", "url"),
    )


# Database connection
_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    """Construct PostgreSQL database URL from environment variables."""
    if not RDS_ENDPOINT:
        raise ValueError("RDS_ENDPOINT environment variable is required")
    if not RDS_PASSWORD:
        raise ValueError("RDS_PASSWORD environment variable is required")
    
    return f"postgresql://{RDS_USERNAME}:{RDS_PASSWORD}@{RDS_ENDPOINT}:{RDS_PORT}/{RDS_DB_NAME}"


def _get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        database_url = _get_database_url()
        # Use NullPool for Lambda compatibility (no connection pooling across invocations)
        _engine = create_engine(
            database_url,
            poolclass=NullPool,
            echo=False,
            connect_args={"connect_timeout": 10}
        )
    return _engine


def _get_session() -> Session:
    """Get database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal()


def _init_database():
    """Initialize database tables (create if they don't exist)."""
    try:
        Base.metadata.create_all(bind=_get_engine())
        print(f"[RDS PostgreSQL] Database initialized - Endpoint: {RDS_ENDPOINT}, DB: {RDS_DB_NAME}")
    except Exception as e:
        print(f"[RDS PostgreSQL] Error initializing database: {e}")
        raise


# Initialize database on import
try:
    _init_database()
except Exception as e:
    print(f"[RDS PostgreSQL] Warning: Could not initialize database: {e}")
    print("   Make sure RDS instance is running and credentials are correct")


def generate_artifact_id() -> ArtifactID:
    """Generate a new artifact ID."""
    return str(uuid.uuid4())


def _normalized(name: Optional[str]) -> Optional[str]:
    """Normalize name for searching."""
    return name.strip().lower() if isinstance(name, str) else None


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


def _model_to_record(db_model: ArtifactModel) -> CodeRecord | DatasetRecord | ModelRecord:
    """Convert database model to appropriate Record type."""
    artifact = _deserialize_artifact(db_model.artifact_data)
    artifact_type = ArtifactType(db_model.artifact_type)

    if artifact_type == ArtifactType.MODEL:
        return ModelRecord(
            artifact=artifact,
            rating=_deserialize_rating(db_model.rating),
            license=db_model.license,
            dataset_id=db_model.dataset_id,
            dataset_name=db_model.dataset_name,
            dataset_url=db_model.dataset_url,
            code_id=db_model.code_id,
            code_name=db_model.code_name,
            code_url=db_model.code_url,
            processing_status=db_model.processing_status or "completed",
        )
    elif artifact_type == ArtifactType.DATASET:
        return DatasetRecord(artifact=artifact)
    else:  # CODE
        return CodeRecord(artifact=artifact)


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
    """Insert or update an artifact entry."""
    session = _get_session()
    try:
        artifact_id = artifact.metadata.id
        artifact_type = artifact.metadata.type

        # Check if exists
        existing = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id
        ).first()

        normalized_name = _normalized(artifact.metadata.name)

        if existing:
            # Update existing
            existing.artifact_type = artifact_type.value
            existing.name = artifact.metadata.name
            existing.name_normalized = normalized_name
            existing.url = artifact.data.url
            existing.artifact_data = _serialize_artifact(artifact)

            if artifact_type == ArtifactType.MODEL:
                if rating is not None:
                    existing.rating = _serialize_rating(rating)
                if license is not None:
                    existing.license = license
                if dataset_name is not None:
                    existing.dataset_name = dataset_name
                    existing.dataset_name_normalized = _normalized(dataset_name)
                if dataset_url is not None:
                    existing.dataset_url = dataset_url
                if code_name is not None:
                    existing.code_name = code_name
                    existing.code_name_normalized = _normalized(code_name)
                if code_url is not None:
                    existing.code_url = code_url
                if processing_status is not None:
                    existing.processing_status = processing_status
        else:
            # Insert new
            db_model = ArtifactModel(
                artifact_id=artifact_id,
                artifact_type=artifact_type.value,
                name=artifact.metadata.name,
                name_normalized=normalized_name,
                url=artifact.data.url,
                artifact_data=_serialize_artifact(artifact),
            )

            if artifact_type == ArtifactType.MODEL:
                db_model.rating = _serialize_rating(rating)
                db_model.license = license
                db_model.dataset_name = dataset_name
                db_model.dataset_name_normalized = _normalized(dataset_name)
                db_model.dataset_url = dataset_url
                db_model.code_name = code_name
                db_model.code_name_normalized = _normalized(code_name)
                db_model.code_url = code_url
                db_model.processing_status = processing_status or "completed"

            session.add(db_model)

        session.commit()
        print(f"[RDS PostgreSQL] Saved artifact: {artifact_type.value}:{artifact_id}")

        # Link dataset/code by name if IDs not set
        if artifact_type == ArtifactType.MODEL and (dataset_name or code_name):
            _link_dataset_code_by_name(session, artifact_id, dataset_name, code_name)

        return artifact
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error saving artifact: {e}")
        raise
    finally:
        session.close()


def _link_dataset_code_by_name(
    session: Session,
    artifact_id: str,
    dataset_name: Optional[str],
    code_name: Optional[str],
) -> None:
    """Link model to dataset/code by name if IDs not set."""
    if dataset_name:
        normalized = _normalized(dataset_name)
        dataset = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == ArtifactType.DATASET.value,
            ArtifactModel.name_normalized == normalized
        ).first()
        if dataset:
            session.query(ArtifactModel).filter(
                ArtifactModel.artifact_id == artifact_id
            ).update({
                "dataset_id": dataset.artifact_id,
                "dataset_url": dataset.url
            })
            session.commit()

    if code_name:
        normalized = _normalized(code_name)
        code = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == ArtifactType.CODE.value,
            ArtifactModel.name_normalized == normalized
        ).first()
        if code:
            session.query(ArtifactModel).filter(
                ArtifactModel.artifact_id == artifact_id
            ).update({
                "code_id": code.artifact_id,
                "code_url": code.url
            })
            session.commit()


def get_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> Optional[Artifact]:
    """Retrieve an artifact by type and ID."""
    session = _get_session()
    try:
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == artifact_type.value
        ).first()

        if not db_model:
            return None

        return _deserialize_artifact(db_model.artifact_data)
    except Exception as e:
        print(f"[RDS PostgreSQL] Error getting artifact: {e}")
        return None
    finally:
        session.close()


def delete_artifact(artifact_type: ArtifactType, artifact_id: ArtifactID) -> bool:
    """Delete an artifact."""
    session = _get_session()
    try:
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == artifact_type.value
        ).first()

        if not db_model:
            return False

        # If deleting dataset/code, unlink from models
        if artifact_type == ArtifactType.DATASET:
            session.query(ArtifactModel).filter(
                ArtifactModel.artifact_type == ArtifactType.MODEL.value,
                ArtifactModel.dataset_id == artifact_id
            ).update({"dataset_id": None, "dataset_url": None})
        elif artifact_type == ArtifactType.CODE:
            session.query(ArtifactModel).filter(
                ArtifactModel.artifact_type == ArtifactType.MODEL.value,
                ArtifactModel.code_id == artifact_id
            ).update({"code_id": None, "code_url": None})

        session.delete(db_model)
        session.commit()
        print(f"[RDS PostgreSQL] Deleted artifact: {artifact_type.value}:{artifact_id}")
        return True
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error deleting artifact: {e}")
        return False
    finally:
        session.close()


def list_metadata(artifact_type: ArtifactType) -> List[ArtifactMetadata]:
    """List all metadata for a given artifact type."""
    session = _get_session()
    try:
        db_models = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == artifact_type.value
        ).all()

        results = []
        for db_model in db_models:
            artifact = _deserialize_artifact(db_model.artifact_data)
            results.append(artifact.metadata)
        return results
    except Exception as e:
        print(f"[RDS PostgreSQL] Error listing metadata: {e}")
        return []
    finally:
        session.close()


def query_artifacts(queries: Iterable[ArtifactQuery]) -> List[ArtifactMetadata]:
    """Query artifacts by name and type."""
    session = _get_session()
    try:
        results: Dict[str, ArtifactMetadata] = {}

        for query in queries:
            types = query.types or [ArtifactType.MODEL, ArtifactType.DATASET, ArtifactType.CODE]
            query_name_normalized = _normalized(query.name) if query.name != "*" else None

            for artifact_type in types:
                query_obj = session.query(ArtifactModel).filter(
                    ArtifactModel.artifact_type == artifact_type.value
                )

                if query_name_normalized:
                    query_obj = query_obj.filter(
                        ArtifactModel.name_normalized == query_name_normalized
                    )

                db_models = query_obj.all()

                for db_model in db_models:
                    artifact = _deserialize_artifact(db_model.artifact_data)
                    metadata = artifact.metadata
                    # Double-check name match (case-insensitive)
                    if query.name == "*" or query.name.lower() == metadata.name.lower():
                        results[f"{metadata.type}:{metadata.id}"] = metadata

        return list(results.values())
    except Exception as e:
        print(f"[RDS PostgreSQL] Error querying artifacts: {e}")
        return []
    finally:
        session.close()


def reset() -> None:
    """Delete all artifacts from the database."""
    session = _get_session()
    try:
        session.query(ArtifactModel).delete()
        session.commit()
        print("[RDS PostgreSQL] Reset: deleted all artifacts")
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error resetting database: {e}")
    finally:
        session.close()


def artifact_exists(artifact_type: ArtifactType, url: str) -> bool:
    """Check if an artifact with the given URL exists."""
    session = _get_session()
    try:
        count = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == artifact_type.value,
            ArtifactModel.url == url
        ).count()
        return count > 0
    except Exception as e:
        print(f"[RDS PostgreSQL] Error checking artifact existence: {e}")
        return False
    finally:
        session.close()


def save_model_rating(artifact_id: ArtifactID, rating: ModelRating) -> None:
    """Save or update a model rating."""
    session = _get_session()
    try:
        session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).update({"rating": _serialize_rating(rating)})
        session.commit()
        print(f"[RDS PostgreSQL] Saved rating for model: {artifact_id}")
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error saving model rating: {e}")
    finally:
        session.close()


def get_model_rating(artifact_id: ArtifactID) -> Optional[ModelRating]:
    """Get the rating for a model."""
    session = _get_session()
    try:
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).first()

        if not db_model:
            return None

        return _deserialize_rating(db_model.rating)
    except Exception as e:
        print(f"[RDS PostgreSQL] Error getting model rating: {e}")
        return None
    finally:
        session.close()


def save_model_license(artifact_id: ArtifactID, license: str) -> None:
    """Save or update a model license."""
    session = _get_session()
    try:
        session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).update({"license": license})
        session.commit()
        print(f"[RDS PostgreSQL] Saved license for model: {artifact_id}")
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error saving model license: {e}")
    finally:
        session.close()


def get_model_license(artifact_id: ArtifactID) -> Optional[str]:
    """Get the license for a model."""
    session = _get_session()
    try:
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).first()

        if not db_model:
            return None

        return db_model.license
    except Exception as e:
        print(f"[RDS PostgreSQL] Error getting model license: {e}")
        return None
    finally:
        session.close()


def get_processing_status(artifact_id: ArtifactID) -> Optional[str]:
    """Get the processing status of a model artifact."""
    session = _get_session()
    try:
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).first()

        if not db_model:
            return None

        return db_model.processing_status or "completed"
    except Exception as e:
        print(f"[RDS PostgreSQL] Error getting processing status: {e}")
        return None
    finally:
        session.close()


def update_processing_status(artifact_id: ArtifactID, status: str) -> None:
    """Update the processing status of a model artifact."""
    session = _get_session()
    try:
        session.query(ArtifactModel).filter(
            ArtifactModel.artifact_id == artifact_id,
            ArtifactModel.artifact_type == ArtifactType.MODEL.value
        ).update({"processing_status": status})
        session.commit()
        print(f"[RDS PostgreSQL] Updated processing status for model: {artifact_id}")
    except Exception as e:
        session.rollback()
        print(f"[RDS PostgreSQL] Error updating processing status: {e}")
    finally:
        session.close()


def find_dataset_by_name(name: str) -> Optional[DatasetRecord]:
    """Find a dataset by normalized name."""
    session = _get_session()
    try:
        normalized = _normalized(name) or ""
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == ArtifactType.DATASET.value,
            ArtifactModel.name_normalized == normalized
        ).first()

        if db_model:
            record = _model_to_record(db_model)
            if isinstance(record, DatasetRecord):
                return record
        return None
    except Exception as e:
        print(f"[RDS PostgreSQL] Error finding dataset by name: {e}")
        return None
    finally:
        session.close()


def find_code_by_name(name: str) -> Optional[CodeRecord]:
    """Find a code artifact by normalized name."""
    session = _get_session()
    try:
        normalized = _normalized(name) or ""
        db_model = session.query(ArtifactModel).filter(
            ArtifactModel.artifact_type == ArtifactType.CODE.value,
            ArtifactModel.name_normalized == normalized
        ).first()

        if db_model:
            record = _model_to_record(db_model)
            if isinstance(record, CodeRecord):
                return record
        return None
    except Exception as e:
        print(f"[RDS PostgreSQL] Error finding code by name: {e}")
        return None
    finally:
        session.close()


# Helper function for regex search in artifacts.py
def _get_all_artifacts_for_regex() -> List[ArtifactMetadata]:
    """Get all artifacts for regex searching."""
    session = _get_session()
    try:
        db_models = session.query(ArtifactModel).all()
        results = []
        for db_model in db_models:
            artifact = _deserialize_artifact(db_model.artifact_data)
            results.append(artifact.metadata)
        return results
    except Exception as e:
        print(f"[RDS PostgreSQL] Error getting all artifacts for regex: {e}")
        return []
    finally:
        session.close()


# Expose for regex search compatibility - create a dict-like structure
class _StoreDict:
    """Dict-like wrapper for RDS storage to match memory._TYPE_TO_STORE interface."""
    def __init__(self, artifact_type: ArtifactType):
        self.artifact_type = artifact_type

    def values(self):
        """Return records for this artifact type."""
        session = _get_session()
        try:
            db_models = session.query(ArtifactModel).filter(
                ArtifactModel.artifact_type == self.artifact_type.value
            ).all()
            for db_model in db_models:
                yield _model_to_record(db_model)
        except Exception as e:
            print(f"[RDS PostgreSQL] Error getting values for {self.artifact_type}: {e}")
            raise
        finally:
            session.close()


_TYPE_TO_STORE = {
    ArtifactType.MODEL: _StoreDict(ArtifactType.MODEL),
    ArtifactType.DATASET: _StoreDict(ArtifactType.DATASET),
    ArtifactType.CODE: _StoreDict(ArtifactType.CODE),
}
