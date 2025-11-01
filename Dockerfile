# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps
COPY dependencies.txt .
RUN pip install --no-cache-dir -r dependencies.txt

# Copy application code
COPY . .

# Default environment variables
ENV LOG_LEVEL=1
ENV LOG_FILE=/tmp/error_logs.log
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port for FastAPI
EXPOSE 8000

# Health check for ECS (using curl instead of requests for lighter weight)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]


