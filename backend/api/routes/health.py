from fastapi import APIRouter  # pyright: ignore[reportMissingImports]

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}