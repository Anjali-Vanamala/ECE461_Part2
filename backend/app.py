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
from starlette.requests import Request

from backend.api.routes import artifacts, health, system, tracks
from backend.middleware.logging import setup_logging
from backend.middleware.rate_limit import setup_rate_limit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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
root_path = "/prod"

app = fastapi.FastAPI(
    title="Model Registry API",
    description="API for storing, rating, and viewing models",
    version="0.1.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    root_path=root_path,  # Set root path for API Gateway stage (e.g., /prod)
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

    Security: Logs detailed error info to CloudWatch only, returns generic message to user.
    """
    # Log full validation error details to CloudWatch (not exposed to user)
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")

    return JSONResponse(
        status_code=400,
        content={"detail": "400: Bad request. There are missing field(s), it is formed improperly, or is invalid.."}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Security: Prevents internal details (stack traces, file paths, DB structure) from leaking to users.
    Logs full exception details to CloudWatch for debugging.
    """
    import traceback

    # Log full exception details to CloudWatch (includes stack trace, etc.)
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}",
        exc_info=True
    )
    logger.error(f"Full traceback: {traceback.format_exc()}")

    # Return generic error message to user (no internal details)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "500: Internal server error. Please contact support if this persists.",
            "error_type": "internal_error"
        }
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
app = setup_rate_limit(app)  # type: ignore[assignment]
