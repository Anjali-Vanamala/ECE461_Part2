from typing import Optional

from fastapi import APIRouter, Path  # pyright: ignore[reportMissingImports]
from fastapi import HTTPException, Query, status

from backend.models.package import (PackageCreate, PackageListResponse,
                                    PackageModel, PackageUpdate)
from backend.services.package_service import (create_package_from_url,
                                              delete_package_by_id,
                                              get_package_by_id,
                                              list_packages_with_filters,
                                              update_package_by_id)

router = APIRouter(prefix="/package", tags=["packages"])


@router.post("/", response_model=PackageModel, status_code=status.HTTP_201_CREATED)
def create_package(package_data: PackageCreate):
    """
    CREATE endpoint - Create a new package from a HuggingFace URL.
    Calculates all metrics using Phase 1 rating system.
    """
    try:
        package = create_package_from_url(package_data.URL)
        return package
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create package: {str(e)}"
        )


# IMPORTANT: Specific routes (/packages, /download) must come before /{model_id:path}
@router.get("/packages", response_model=PackageListResponse)
def list_packages(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of items to return"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    LIST endpoint - List packages with pagination and optional filters.
    """
    packages_list, total = list_packages_with_filters(skip, limit, name, category)

    return PackageListResponse(
        items=packages_list,
        total=total,
        offset=skip,
        limit=limit
    )


@router.get("/download/{model_id:path}")
def download_package(model_id: str = Path(..., description="Package ID (can contain slashes)"), content: str = Query("full", description="Content type to download")):
    """
    DOWNLOAD endpoint - Download package content.
    Supports: 'full' (all data), 'metadata' (basic info only)
    """
    package = get_package_by_id(model_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{model_id}' not found"
        )

    if content == "metadata":
        return {
            "id": package.id,
            "name": package.name,
            "category": package.category,
            "URL": package.URL,
            "description": package.description
        }
    elif content == "full":
        return package
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{content}'. Use 'full' or 'metadata'"
        )


@router.get("/{model_id:path}", response_model=PackageModel)
def get_package(model_id: str = Path(..., description="Package ID (can contain slashes)")):
    """
    READ endpoint - Get a package by ID.
    """
    package = get_package_by_id(model_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{model_id}' not found"
        )
    return package


@router.put("/{model_id:path}", response_model=PackageModel)
def update_package(updates: PackageUpdate, model_id: str = Path(..., description="Package ID (can contain slashes)")):
    """
    UPDATE endpoint - Update a package by ID.
    Only updates fields that are provided in the request body.
    """
    updated_package = update_package_by_id(model_id, updates)
    if not updated_package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{model_id}' not found"
        )
    return updated_package


@router.delete("/{model_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(model_id: str = Path(..., description="Package ID (can contain slashes)")):
    """
    DELETE endpoint - Delete a package by ID.
    """
    success = delete_package_by_id(model_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package with ID '{model_id}' not found"
        )
    return None
