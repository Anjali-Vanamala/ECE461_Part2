#!/bin/bash
# Package Lambda function for deployment
# Creates a zip file with all dependencies and code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/lambda-build"
ZIP_FILE="$PROJECT_ROOT/lambda-deployment.zip"

echo "Packaging Lambda function..."

# Clean previous build
rm -rf "$BUILD_DIR"
rm -f "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# Copy application code
echo "Copying application code..."
cp -r "$PROJECT_ROOT/backend" "$BUILD_DIR/"
cp -r "$PROJECT_ROOT/metrics" "$BUILD_DIR/" 2>/dev/null || true
cp -r "$PROJECT_ROOT/metrics_helpers" "$BUILD_DIR/" 2>/dev/null || true

# Install dependencies
echo "Installing Python dependencies..."
pip install -r "$PROJECT_ROOT/dependencies.txt" -t "$BUILD_DIR" --quiet

# Remove unnecessary files to reduce package size
echo "Cleaning up unnecessary files..."
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyd" -delete 2>/dev/null || true

# Create zip file
echo "Creating deployment package..."
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q

# Get package size
PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Lambda package created: $ZIP_FILE ($PACKAGE_SIZE)"

# Check if package is too large (Lambda limit is 50MB for direct upload, 250MB unzipped)
ZIP_SIZE_MB=$(du -m "$ZIP_FILE" | cut -f1)
if [ "$ZIP_SIZE_MB" -gt 50 ]; then
    echo "Warning: Package size ($ZIP_SIZE_MB MB) exceeds 50MB direct upload limit"
    echo "   Consider using Lambda layers or container images for deployment"
fi

# Clean up build directory
rm -rf "$BUILD_DIR"

echo "Packaging complete!"
