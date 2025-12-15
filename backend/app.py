"""
FastAPI application for the Model Registry API.

Features:
- Loads environment variables from a `.env` file if present.
- Configures logging and CORS middleware.
- Handles request validation errors with a custom 400 response.
- Includes routers for health, artifacts, system, and tracks endpoints.
- Provides a root endpoint (`/`) returning a simple welcome message.

API:
    Title: Model Registry API
    Version: 0.1.0
    License: MIT
"""
import logging
import os
from pathlib import Path

import fastapi  # pyright: ignore[reportMissingImports]
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import artifacts, health, system, tracks
from backend.middleware.logging import setup_logging

logging.basicConfig(level=logging.INFO)
# Load .env file if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Hardcode /prod for API Gateway stage path
# API Gateway strips /prod before forwarding, so route handlers remain unchanged
ROOT_PATH = "/prod"

app = fastapi.FastAPI(
    title="Model Registry API",
    description="API for storing, rating, and viewing models",
    version="0.1.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    root_path=ROOT_PATH,  # Set root path for API Gateway stage (e.g., /prod)
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins (e.g., S3 bucket URL)
    allow_credentials=False,  # Set to False when using wildcard origins (browser requirement)
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Handle request validation errors.

    Returns a 400 JSON response when the incoming request is malformed
    or missing required fields.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": "400: Bad request. There are missing field(s), it is formed improperly, or is invalid.."}
    )


app.include_router(health.router)
app.include_router(artifacts.router)
app.include_router(system.router)
app.include_router(tracks.router)


@app.get("/")
def read_root():
    """
    Root endpoint of the API.

    Returns a simple welcome message.
    """
    return {"message": "Hello, World!"}


app = setup_logging(app)  # type: ignore[assignment]
