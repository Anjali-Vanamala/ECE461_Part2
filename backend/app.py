import os
from pathlib import Path

import fastapi  # pyright: ignore[reportMissingImports]

from backend.api.routes import artifacts, health, system

# Load .env file if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

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
app.include_router(artifacts.router)
app.include_router(system.router)


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
