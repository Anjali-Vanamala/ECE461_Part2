import fastapi  # pyright: ignore[reportMissingImports]

from backend.api.routes import health, ingest, package
from backend.middleware.logging import LoggingMiddleware

app = fastapi.FastAPI(
    title="Model Registry API",
    description="API for storing, rating, and viewing models",
    version="0.1.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add logging middleware for request/error logging and CloudWatch metrics
app.add_middleware(LoggingMiddleware)

app.include_router(health.router)
app.include_router(package.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
