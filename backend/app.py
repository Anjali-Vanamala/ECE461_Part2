import fastapi  # pyright: ignore[reportMissingImports]

from backend.api.routes import (health, ingest, license_compat, package,
                                size_cost)

app = fastapi.FastAPI(
    title="Model Registry API",
    description="API for storing, rating, and viewing models",
    version="0.1.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

app.include_router(health.router)
app.include_router(package.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(size_cost.router, prefix="/api/v1")
app.include_router(license_compat.router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
