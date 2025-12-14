import json
import logging
import os
import subprocess
import threading
import glob
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
    """Run the Python download benchmark script in a background thread"""
    import traceback
    
    logger.info(f"Starting download benchmark job {job_id}")
    
    try:
        # Get the script path (project root)
        script_path = Path(__file__).parent.parent.parent.parent / "benchmark_concurrent_download.py"
        
        logger.info(f"Looking for script at: {script_path}")
        
        if not script_path.exists():
            error_msg = f"Benchmark script not found at {script_path}"
            logger.error(error_msg)
            download_benchmark_jobs[job_id]["status"] = "failed"
            download_benchmark_jobs[job_id]["error"] = error_msg
            return
        
        # Find Python executable
        python_cmd = "python3"
        import shutil
        if not shutil.which(python_cmd):
            python_cmd = "python"
            if not shutil.which(python_cmd):
                error_msg = "Python not found. Please ensure Python 3 is installed and in PATH."
                logger.error(error_msg)
                download_benchmark_jobs[job_id]["status"] = "failed"
                download_benchmark_jobs[job_id]["error"] = error_msg
                return
        
        download_benchmark_jobs[job_id]["progress"] = "Executing Python benchmark script..."
        download_benchmark_jobs[job_id]["current_progress"] = "0/100"  # Track X/100 downloads
        logger.info(f"Executing Python script: {python_cmd} {script_path}")
        logger.info("This may take 3-5 minutes to complete...")
        
        # Run the script with real-time output capture
        import re
        # Use -u flag for unbuffered output to ensure real-time progress
        process = subprocess.Popen(
            [python_cmd, "-u", str(script_path)],  # -u = unbuffered
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            cwd=str(script_path.parent)
        )
        
        # Capture stdout line by line to extract progress
        stdout_lines = []
        stderr_lines = []
        
        # Progress regex pattern: "  Progress: 12/100 completed" (more flexible)
        progress_pattern = re.compile(r'Progress:\s*(\d+)/(\d+)\s+completed', re.IGNORECASE)
        # ANSI escape code pattern (for removing color codes)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        def read_output(pipe, lines_list, is_stderr=False):
            """Read output from pipe and update progress"""
            try:
                for line in iter(pipe.readline, ''):
                    if not line:
                        break
                    line = line.rstrip()
                    lines_list.append(line)
                    
                    # Parse progress updates (strip ANSI codes first)
                    if not is_stderr:
                        # Remove ANSI color codes for parsing
                        clean_line = ansi_escape.sub('', line)
                        match = progress_pattern.search(clean_line)
                        if match:
                            completed = match.group(1)
                            total = match.group(2)
                            progress_str = f"{completed}/{total}"
                            download_benchmark_jobs[job_id]["current_progress"] = progress_str
                            download_benchmark_jobs[job_id]["progress"] = f"Downloading... {progress_str} completed"
                            logger.info(f"Progress update: {progress_str}")
                        # Debug: log lines that contain "Progress" but didn't match
                        elif "Progress" in clean_line.lower() or "completed" in clean_line.lower():
                            logger.debug(f"Progress-like line that didn't match: {clean_line[:100]}")
            except Exception as e:
                logger.error(f"Error reading output: {e}")
            finally:
                pipe.close()
        
        # Start threads to read stdout and stderr
        import threading
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_lines))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_lines, True))
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete
        return_code = process.wait(timeout=600)  # 10 minute timeout
        
        # Wait for output threads to finish
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        stdout_text = '\n'.join(stdout_lines)
        stderr_text = '\n'.join(stderr_lines)
        
        logger.info(f"Script completed with return code: {return_code}")
        logger.info(f"Script stdout length: {len(stdout_text)} chars")
        logger.info(f"Script stderr length: {len(stderr_text)} chars")
        
        if stdout_text:
            logger.info(f"Script stdout (last 1000 chars): {stdout_text[-1000:]}")
        if stderr_text:
            logger.warning(f"Script stderr: {stderr_text}")
        
        result = type('Result', (), {
            'returncode': return_code,
            'stdout': stdout_text,
            'stderr': stderr_text
        })()
        
        if result.returncode != 0:
            error_msg = (
                f"Benchmark script failed with return code {result.returncode}. "
                f"Error: {result.stderr[:1000] if result.stderr else 'No error output'}. "
                f"Stdout: {result.stdout[-500:] if result.stdout else 'None'}"
            )
            logger.error(error_msg)
            download_benchmark_jobs[job_id]["status"] = "failed"
            download_benchmark_jobs[job_id]["error"] = error_msg
            download_benchmark_jobs[job_id]["stdout"] = result.stdout[-2000:] if result.stdout else None
            download_benchmark_jobs[job_id]["stderr"] = result.stderr[-2000:] if result.stderr else None
            return
        
        download_benchmark_jobs[job_id]["progress"] = "Looking for output file..."
        output_dir = script_path.parent
        json_files = glob.glob(str(output_dir / "benchmark_download_concurrent_*.json"))
        
        logger.info(f"Found {len(json_files)} JSON output files")
        
        if not json_files:
            error_msg = (
                "Benchmark script did not generate output file. "
                f"Script stdout: {result.stdout[:500] if result.stdout else 'None'}"
            )
            logger.error(error_msg)
            download_benchmark_jobs[job_id]["status"] = "failed"
            download_benchmark_jobs[job_id]["error"] = error_msg
            download_benchmark_jobs[job_id]["stdout"] = result.stdout[-2000:] if result.stdout else None
            return
        
        latest_json = max(json_files, key=os.path.getctime)
        logger.info(f"Using output file: {latest_json}")
        
        with open(latest_json, 'r', encoding='utf-8') as f:
            benchmark_data = json.load(f)
        
        download_benchmark_jobs[job_id]["status"] = "completed"
        download_benchmark_jobs[job_id]["results"] = benchmark_data
        download_benchmark_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        download_benchmark_jobs[job_id]["progress"] = "Completed successfully"
        logger.info(f"Download benchmark job {job_id} completed successfully")
        logger.info(f"Results keys: {list(benchmark_data.keys()) if isinstance(benchmark_data, dict) else 'Not a dict'}")
        
    except subprocess.TimeoutExpired:
        error_msg = "Benchmark script timed out after 10 minutes"
        logger.error(error_msg)
        download_benchmark_jobs[job_id]["status"] = "failed"
        download_benchmark_jobs[job_id]["error"] = error_msg
        download_benchmark_jobs[job_id]["progress"] = "Timed out"
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse benchmark output JSON: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Full traceback: {traceback.format_exc()}")
        download_benchmark_jobs[job_id]["status"] = "failed"
        download_benchmark_jobs[job_id]["error"] = error_msg
        download_benchmark_jobs[job_id]["progress"] = "JSON parsing failed"
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
