from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["tracks"])


@router.get("/tracks",
            status_code=status.HTTP_200_OK,
            summary="Get the list of tracks a student has planned to implement in their code",)
async def get_planned_tracks():
    try:
        return {"plannedTracks": ["Performance track"]}
    except Exception as exc:
        raise HTTPException(status_code=500,
                            detail="The system encountered an error while retrieving the student's track information.") from exc
