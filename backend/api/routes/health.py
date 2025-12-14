import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Query, HTTPException

from backend.models import (HealthComponentBrief, HealthComponentCollection,
                            HealthComponentDetail, HealthIssue,
                            HealthLogReference, HealthRequestSummary,
                            HealthStatus, HealthSummaryResponse,
                            HealthTimelineEntry)
from backend.services.metrics_tracker import (get_request_summary,
                                              get_requests_per_minute,
                                              get_timeline, get_uptime_seconds)

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

# Download benchmark job tracking
download_benchmark_jobs: Dict[str, Dict] = {}
active_download_benchmark_threads: Dict[str, threading.Thread] = {}


@router.get("/health", summary="Heartbeat check (BASELINE)")
async def health_summary() -> HealthSummaryResponse:
    now = datetime.now(timezone.utc)
    window_minutes = 60

    # Get real request summary
    request_summary_data = get_request_summary(window_minutes)
    request_summary = HealthRequestSummary(
        window_start=request_summary_data["window_start"],
        window_end=request_summary_data["window_end"],
        total_requests=request_summary_data["total_requests"],
        per_route=request_summary_data["per_route"],
        per_artifact_type=request_summary_data["per_artifact_type"],
        unique_clients=request_summary_data["unique_clients"],
    )

    # Determine overall status (OK if no errors in recent requests)
    # You can make this more sophisticated
    status = HealthStatus.OK

    summary = HealthSummaryResponse(
        status=status,
        checked_at=now,
        window_minutes=window_minutes,
        uptime_seconds=get_uptime_seconds(),
        version="0.1.0",
        request_summary=request_summary,
        components=[
            HealthComponentBrief(
                id="api",
                status=status,
                display_name="API Service",
                issue_count=0,
                last_event_at=now,
            )
        ],
        logs=[],
    )
    return summary


@router.get(
    "/health/components",
    summary="Get component health details (NON-BASELINE)",
)
async def health_components(
    window_minutes: int = Query(60, ge=5, le=1440),
    include_timeline: bool = Query(False),
) -> HealthComponentCollection:
    now = datetime.now(timezone.utc)

    # Get real metrics
    requests_per_min = get_requests_per_minute(window_minutes)
    timeline_data = get_timeline(window_minutes) if include_timeline else []

    # Determine status based on metrics
    status = HealthStatus.OK
    if requests_per_min == 0 and window_minutes >= 60:
        # No requests in last hour might indicate an issue
        status = HealthStatus.DEGRADED

    timeline = [
        HealthTimelineEntry(
            bucket=entry["bucket"],
            value=entry["value"],
            unit=entry["unit"],
        )
        for entry in timeline_data
    ]

    detail = HealthComponentDetail(
        id="api",
        display_name="API Service",
        status=status,
        observed_at=now,
        description="Main API service handling requests.",
        metrics={
            "requests_per_minute": round(requests_per_min, 2),
            "uptime_hours": round(get_uptime_seconds() / 3600, 2),
        },
        issues=[
            HealthIssue(
                code="none", severity="info", summary="No issues", details=None
            ),
        ],
        timeline=timeline,
        logs=[
            HealthLogReference(
                label="API Access",
                url="http://example.com/logs/api_access",
                tail_available=True,
                last_updated_at=now,
            )
        ],
    )
    return HealthComponentCollection(
        components=[detail],
        generated_at=now,
        window_minutes=window_minutes,
    )


def run_download_benchmark_script(job_id: str):
    """Run the Python download benchmark function in a background thread"""
    import traceback
    import sys
    import asyncio
    from pathlib import Path
    
    logger.info(f"Starting download benchmark job {job_id}")
    
    try:
        # Import the benchmark function directly
        # Add project root to path to import the script
        project_root = Path(__file__).parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        try:
            from benchmark_concurrent_download import run_benchmark
        except ImportError as e:
            error_msg = f"Failed to import benchmark function: {e}"
            logger.error(error_msg)
            download_benchmark_jobs[job_id]["status"] = "failed"
            download_benchmark_jobs[job_id]["error"] = error_msg
            return
        
        download_benchmark_jobs[job_id]["progress"] = "Initializing benchmark..."
        download_benchmark_jobs[job_id]["current_progress"] = "0/100"  # Track X/100 downloads
        logger.info("Starting benchmark function...")
        logger.info("This may take 3-5 minutes to complete...")
        
        # Progress callback to update job status
        def progress_callback(completed: int, total: int, successful: int, failed: int):
            """Update job progress from benchmark callback"""
            try:
                progress_str = f"{completed}/{total}"
                download_benchmark_jobs[job_id]["current_progress"] = progress_str
                download_benchmark_jobs[job_id]["progress"] = f"Downloading... {progress_str} completed"
                logger.info(f"Progress update: {progress_str} ({successful} successful, {failed} failed)")
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        # Get API base URL from environment or use AWS API Gateway (production)
        # For local testing, set API_BASE_URL=http://localhost:8000
        api_base_url = os.getenv("API_BASE_URL", "https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod")
        
        # Create a new event loop for this thread to avoid interfering with FastAPI's event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async benchmark function
            download_benchmark_jobs[job_id]["progress"] = "Running benchmark..."
            results = loop.run_until_complete(
                run_benchmark(
                    base_url=api_base_url,
                    progress_callback=progress_callback
                )
            )
            
            # Store results
            download_benchmark_jobs[job_id]["status"] = "completed"
            download_benchmark_jobs[job_id]["results"] = results
            download_benchmark_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            download_benchmark_jobs[job_id]["progress"] = "Completed successfully"
            download_benchmark_jobs[job_id]["current_progress"] = None  # Clear progress on completion
            logger.info(f"Download benchmark job {job_id} completed successfully")
            logger.info(f"Results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}")
        finally:
            # Clean up the event loop
            loop.close()
        
    except ValueError as e:
        # Tiny-LLM not found
        error_msg = f"Benchmark failed: {str(e)}"
        logger.error(error_msg)
        download_benchmark_jobs[job_id]["status"] = "failed"
        download_benchmark_jobs[job_id]["error"] = error_msg
        download_benchmark_jobs[job_id]["progress"] = "Failed: Model not found"
    except RuntimeError as e:
        # Runtime errors (e.g., no successful downloads)
        error_msg = f"Benchmark failed: {str(e)}"
        logger.error(error_msg)
        # Include full error message (not truncated) for debugging
        download_benchmark_jobs[job_id]["status"] = "failed"
        download_benchmark_jobs[job_id]["error"] = error_msg
        download_benchmark_jobs[job_id]["progress"] = f"Failed: {str(e)[:200]}"
    except Exception as e:
        error_msg = f"Error executing benchmark: {str(e)}"
        logger.exception(f"Exception in download benchmark job {job_id}: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        download_benchmark_jobs[job_id]["status"] = "failed"
        download_benchmark_jobs[job_id]["error"] = error_msg
        download_benchmark_jobs[job_id]["progress"] = f"Error: {str(e)[:100]}"
    finally:
        if job_id in active_download_benchmark_threads:
            thread = active_download_benchmark_threads[job_id]
            if thread.is_alive():
                logger.warning(f"Thread for job {job_id} is still alive during cleanup")
            else:
                logger.info(f"Thread for job {job_id} has completed")
            del active_download_benchmark_threads[job_id]
            logger.info(f"Cleaned up thread reference for job {job_id}")


@router.post("/health/download-benchmark/start", summary="Start download benchmark")
async def start_download_benchmark() -> Dict:
    """
    Start the download benchmark script in a background thread.
    Returns a job_id that can be used to check status and get results.
    """
    import uuid
    
    # Check if there's already a running benchmark
    running_jobs = [
        job_id for job_id, job in download_benchmark_jobs.items()
        if job.get("status") == "running"
    ]
    
    if running_jobs:
        raise HTTPException(
            status_code=409,
            detail=f"A benchmark is already running (job_id: {running_jobs[0]})"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    download_benchmark_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "progress": "Initializing...",
        "current_progress": "0/100",  # Track X/100 downloads
        "results": None,
        "error": None,
    }
    
    # Start benchmark in background thread
    thread = threading.Thread(
        target=run_download_benchmark_script,
        args=(job_id,),
        daemon=True
    )
    thread.start()
    active_download_benchmark_threads[job_id] = thread
    
    logger.info(f"Started download benchmark job {job_id}")
    
    return {
        "job_id": job_id,
        "status": "running",
        "message": "Download benchmark started"
    }


@router.get("/health/download-benchmark/{job_id}", summary="Get download benchmark status")
async def get_download_benchmark_status(job_id: str) -> Dict:
    """
    Get the status and results of a download benchmark job.
    """
    if job_id not in download_benchmark_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = download_benchmark_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "started_at": job.get("started_at"),
        "progress": job.get("progress"),
        "current_progress": job.get("current_progress"),  # X/100 format
    }
    
    if job.get("status") == "completed":
        response["results"] = job.get("results")
        response["completed_at"] = job.get("completed_at")
    elif job.get("status") == "failed":
        response["error"] = job.get("error")
        response["stdout"] = job.get("stdout")
        response["stderr"] = job.get("stderr")
    
    return response
