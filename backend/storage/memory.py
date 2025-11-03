"""
In-memory storage for packages (Phase 2).
This will be replaced with DynamoDB in Phase 3.
"""
from typing import Dict, Optional

from backend.models.package import PackageModel

# In-memory dictionary: key = package_id, value = PackageModel
packages: Dict[str, PackageModel] = {}


def get_package(package_id: str) -> Optional[PackageModel]:
    """Get a package by ID"""
    return packages.get(package_id)


def create_package(package: PackageModel) -> PackageModel:
    """Store a new package"""
    packages[package.id] = package
    return package


def update_package(package_id: str, package: PackageModel) -> Optional[PackageModel]:
    """Update an existing package"""
    if package_id not in packages:
        return None
    packages[package_id] = package
    return package


def delete_package(package_id: str) -> bool:
    """Delete a package by ID"""
    if package_id in packages:
        del packages[package_id]
        return True
    return False


def list_packages(offset: int = 0, limit: int = 100, name_filter: Optional[str] = None, category_filter: Optional[str] = None) -> list[PackageModel]:
    """List packages with optional filters"""
    result = list(packages.values())

    # Apply filters
    if name_filter:
        result = [p for p in result if name_filter.lower() in p.name.lower()]

    if category_filter:
        result = [p for p in result if p.category == category_filter]

    # Pagination
    return result[offset:offset + limit]


def get_total_count(name_filter: Optional[str] = None, category_filter: Optional[str] = None) -> int:
    """Get total count of packages after applying filters"""
    if not name_filter and not category_filter:
        return len(packages)

    result = list(packages.values())
    if name_filter:
        result = [p for p in result if name_filter.lower() in p.name.lower()]
    if category_filter:
        result = [p for p in result if p.category == category_filter]
    return len(result)
