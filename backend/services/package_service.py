"""
Service layer for package CRUD operations.
"""
from typing import Optional
from backend.models.package import PackageModel, PackageUpdate
from backend.storage.memory import (
    get_package,
    create_package,
    update_package,
    delete_package,
    list_packages,
    get_total_count
)
from backend.services.rating_service import calculate_package_metrics


def create_package_from_url(url: str) -> PackageModel:
    """
    Create a new package by calculating metrics from a URL.
    """
    # Calculate all metrics
    package = calculate_package_metrics(url)
    
    # Store in memory
    create_package(package)
    
    return package


def get_package_by_id(package_id: str) -> Optional[PackageModel]:
    """Get a package by ID"""
    return get_package(package_id)


def update_package_by_id(package_id: str, updates: PackageUpdate) -> Optional[PackageModel]:
    """
    Update a package by ID.
    Only updates fields that are provided (not None).
    """
    existing_package = get_package(package_id)
    if not existing_package:
        return None
    
    # Create updated package with only changed fields
    update_dict = updates.dict(exclude_unset=True)
    updated_package = existing_package.model_copy(update=update_dict)
    
    return update_package(package_id, updated_package)


def delete_package_by_id(package_id: str) -> bool:
    """Delete a package by ID"""
    return delete_package(package_id)


def list_packages_with_filters(
    offset: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    category: Optional[str] = None
) -> tuple[list[PackageModel], int]:
    """
    List packages with optional filters.
    Returns (packages_list, total_count)
    """
    packages_list = list_packages(offset, limit, name, category)
    total = get_total_count(name, category)
    
    return packages_list, total

