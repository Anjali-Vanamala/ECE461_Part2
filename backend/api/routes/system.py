from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/status", summary="Placeholder system endpoint")
async def system_status() -> dict[str, str]:
    return {"message": "System routes under construction"}
