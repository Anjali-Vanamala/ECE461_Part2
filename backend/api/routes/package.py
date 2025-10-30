from fastapi import APIRouter  # pyright: ignore[reportMissingImports]

router = APIRouter(prefix="/package", tags=["packages"])


@router.post("/")
def create_package():
    """CREATE endpoint"""
    pass


@router.get("/{model_id}")
def get_package(model_id: str):
    """READ endpoint"""
    pass


@router.get("/packages")
def list_packages(skip: int = 0, limit: int = 100):
    """LIST endpoint"""
    pass


@router.put("/{model_id}")
def update_package(model_id: str):
    """UPDATE endpoint"""
    pass


@router.delete("/{model_id}")
def delete_package(model_id: str):
    """DELETE endpoint"""
    pass


@router.get("/{model_id}/download")
def download_package(model_id: str, content: str = "full"):
    """DOWNLOAD endpoint"""
    pass
