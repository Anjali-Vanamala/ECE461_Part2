from fastapi import APIRouter  # pyright: ignore[reportMissingImports]



router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/")
def ingest_package():
    """INGEST endpoint"""
    pass