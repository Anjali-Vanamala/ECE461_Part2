"""
System API endpoints.

Currently provides placeholder endpoints for system-related checks.
"""
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/status", summary="Placeholder system endpoint")
async def system_status() -> dict[str, str]:
    """
    Placeholder endpoint for system status."""
    return {"message": "System routes under construction"}
