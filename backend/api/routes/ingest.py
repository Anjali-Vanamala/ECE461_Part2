from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import ingestion

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request model for ingestion endpoint"""
    URL: str = Field(..., description="HuggingFace model URL")


class IngestResponse(BaseModel):
    """Response model for ingestion endpoint"""
    message: str
    ingested: bool


@router.post("/", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def ingest_package(request: IngestRequest):
    """
    INGEST endpoint - Ingest a package from a HuggingFace URL.
    Uses ingestion.py to validate metrics and determine if package should be ingested.
    Returns True if all metrics are above threshold (0.5), False otherwise.
    """
    try:
        result = ingestion.ingest(request.URL)

        # ingestion.ingest returns True/False or None on error
        if result is True:
            return IngestResponse(
                message=f"Package '{request.URL}' successfully ingested",
                ingested=True
            )
        else:
            return IngestResponse(
                message=f"Package '{request.URL}' failed ingestion (metrics below threshold or error occurred)",
                ingested=False
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest package: {str(e)}"
        )
