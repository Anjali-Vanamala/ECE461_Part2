"""
Tracks API endpoints.

Provides endpoints related to students' planned tracks in the system.
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["tracks"])


@router.get("/tracks",
            status_code=status.HTTP_200_OK,
            summary="Get the list of tracks a student has planned to implement in their code",)
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
