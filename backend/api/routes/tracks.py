"""
Tracks API endpoints.

Provides endpoints related to students' planned tracks in the system.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["tracks"])


@router.get(
    "/tracks",
    summary="Get the list of tracks a student has planned.",
    responses={
        200: {
            "description": "Successfully retrieved planned tracks.",
            "content": {
                "application/json": {
                    "example": {
                        "plannedTracks": ["Performance track"]
                    }
                }
            },
        },
        500: {"description": "Internal server error while retrieving track information."},
    },
)
async def get_planned_tracks():
    """
    Retrieve the list of tracks that a student has planned.

    Returns a JSON object with a list of planned tracks.
    """
    try:
        return {"plannedTracks": ["Performance track"]}
    except Exception as exc:
        raise HTTPException(status_code=500,
                            detail="The system encountered an error while retrieving the student's track information.") from exc
