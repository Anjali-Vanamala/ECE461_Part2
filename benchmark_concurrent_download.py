#!/usr/bin/env python3
"""
Concurrent Download Benchmark Script
Performs 100 concurrent downloads of Tiny-LLM and measures performance metrics.
"""

import asyncio
import aiohttp
import json
import os
import sys
import ssl
import certifi
from datetime import datetime
from typing import Dict, List, Optional, Callable
import statistics

# ================================
# CONFIGURATION
# ================================
# Default to deployed API Gateway (production)
BASE_URL = "https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod"
# For local testing, uncomment:
# BASE_URL = "http://localhost:8000"

# Tiny-LLM HuggingFace URL
TINY_LLM_URL = "https://huggingface.co/arnir0/Tiny-LLM"

# Benchmark configuration
CONCURRENT_REQUESTS = 100  # Total number of requests to make
TIMEOUT_SECONDS = 300  # 5 minutes per request

# Note: Files are downloaded but not saved to disk (only measured for metrics)


async def find_tiny_llm_artifact_id(session: aiohttp.ClientSession, base_url: str) -> str:
    """Find Tiny-LLM artifact ID using regex search endpoint"""
    url = f"{base_url}/artifact/byRegEx"
    payload = {"regex": "Tiny-LLM"}
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 404:
                raise ValueError(f"Tiny-LLM not found in registry. Please ingest it first. URL: {TINY_LLM_URL}")
            
            response.raise_for_status()
            artifacts = await response.json()
            
            if not artifacts:
                raise ValueError(f"Tiny-LLM not found in registry. Please ingest it first. URL: {TINY_LLM_URL}")
            
            # Filter to models only and get the first one
            tiny_llm = next((a for a in artifacts if a.get('type') == 'model'), None)
            
            if not tiny_llm:
                raise ValueError(f"Tiny-LLM model not found in registry. Please ingest it first. URL: {TINY_LLM_URL}")
            
            artifact_id = tiny_llm['id']
            return artifact_id
            
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise RuntimeError(f"Failed to find artifact: {e}") from e


async def download_one(
    session: aiohttp.ClientSession,
    download_url: str,
    request_id: int,
    timeout: aiohttp.ClientTimeout
) -> Dict:
    """Download a single file asynchronously"""
    result = {
        'request_id': request_id,
        'start_time': None,
        'end_time': None,
        'total_time_ms': 0,
        'status_code': None,
        'redirect_time_ms': 0,
        'redirect_url': None,
        'response_size_bytes': 0,
        'error': None,
        'success': False
    }
    
    try:
        start_time = datetime.now()
        result['start_time'] = start_time.isoformat()
        
        # Make initial request (don't follow redirects automatically)
        try:
            async with session.get(
                download_url,
                allow_redirects=False,
                timeout=timeout
            ) as response:
                result['status_code'] = response.status
                
                if response.status == 302:
                    # Handle redirect (S3 pre-signed URL)
                    redirect_time = (datetime.now() - start_time).total_seconds() * 1000
                    result['redirect_time_ms'] = round(redirect_time, 2)
                    
                    # Get redirect URL from Location header
                    redirect_url = response.headers.get('Location')
                    if not redirect_url:
                        raise Exception("302 redirect received but no Location header found")
                    
                    result['redirect_url'] = redirect_url
                    
                    # Download from redirect URL
                    async with session.get(redirect_url, timeout=timeout) as download_response:
                        download_response.raise_for_status()
                        content = await download_response.read()
                        result['response_size_bytes'] = len(content)
                        
                        # Content downloaded and measured, but not saved to disk
                        # (discarded after measurement to save space)
                        del content  # Free memory immediately
                        
                        result['success'] = True
                        
                elif response.status == 200:
                    # Handle direct download (proxy)
                    content = await response.read()
                    result['response_size_bytes'] = len(content)
                    
                    # Content downloaded and measured, but not saved to disk
                    # (discarded after measurement to save space)
                    del content  # Free memory immediately
                    
                    result['success'] = True
                else:
                    raise Exception(f"Unexpected status code: {response.status}")
                    
        except aiohttp.ClientResponseError as e:
            result['status_code'] = e.status
            result['error'] = f"HTTP {e.status}: {e.message}"
        except Exception as e:
            result['error'] = str(e)
            
    except Exception as e:
        result['error'] = str(e)
    
    finally:
        end_time = datetime.now()
        result['end_time'] = end_time.isoformat()
        if result['start_time']:
            total_time = (end_time - datetime.fromisoformat(result['start_time'])).total_seconds() * 1000
            result['total_time_ms'] = round(total_time, 2)
    
    return result


async def run_benchmark(
    base_url: Optional[str] = None,
    concurrent_requests: int = CONCURRENT_REQUESTS,
    timeout_seconds: int = TIMEOUT_SECONDS,
    progress_callback: Optional[Callable[[int, int, int, int], None]] = None
) -> Dict:
    """
    Main benchmark function.
    
    Args:
        base_url: API base URL (defaults to BASE_URL constant)
        concurrent_requests: Number of concurrent download requests (defaults to CONCURRENT_REQUESTS)
        timeout_seconds: Timeout per request in seconds (defaults to TIMEOUT_SECONDS)
        progress_callback: Optional callback function(completed, total, successful, failed) for progress updates
    
    Returns:
        Dictionary containing benchmark results
    
    Raises:
        ValueError: If Tiny-LLM is not found in registry
        RuntimeError: If benchmark execution fails
    """
    if base_url is None:
        base_url = BASE_URL
    
    # Create aiohttp session with timeout
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    
    # SSL context using certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    connector = aiohttp.TCPConnector(
        limit=200,  # Allow up to 200 concurrent connections
        ssl=ssl_context
    )
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Step 1: Find artifact ID
        artifact_id = await find_tiny_llm_artifact_id(session, base_url)
        
        # Step 2: Perform concurrent downloads
        download_url = f"{base_url}/artifacts/model/{artifact_id}/download"
        
        overall_start = datetime.now()
        
        # Create all download tasks
        tasks = [
            download_one(session, download_url, i, timeout)
            for i in range(1, concurrent_requests + 1)
        ]
        
        # Track progress (use a dict for thread-safe updates)
        all_results = [None] * concurrent_requests
        progress = {'completed': 0, 'successful': 0, 'failed': 0}
        
        async def progress_reporter():
            """Background task to report progress updates every 2 seconds"""
            while progress['completed'] < concurrent_requests:
                await asyncio.sleep(2.0)
                if progress['completed'] < concurrent_requests and progress_callback:
                    # Call progress callback: (completed, total, successful, failed)
                    try:
                        progress_callback(
                            progress['completed'],
                            concurrent_requests,
                            progress['successful'],
                            progress['failed']
                        )
                    except Exception:
                        # Don't let callback errors break the benchmark
                        pass
        
        # Start progress reporter task
        progress_task = asyncio.create_task(progress_reporter())
        
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    
                    # Store result (download_one always returns a dict, even on error)
                    request_id = result.get('request_id', 0)
                    if request_id > 0:
                        all_results[request_id - 1] = result
                    else:
                        # Fallback: append if we can't determine request_id
                        all_results.append(result)
                    
                    # Update counters
                    progress['completed'] += 1
                    if result.get('success', False):
                        progress['successful'] += 1
                    else:
                        progress['failed'] += 1
                        
                except Exception as e:
                    # Handle unexpected exceptions (shouldn't happen, but safety net)
                    progress['completed'] += 1
                    progress['failed'] += 1
        finally:
            # Cancel progress reporter when done
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            # Final progress update
            if progress_callback:
                try:
                    progress_callback(
                        progress['completed'],
                        concurrent_requests,
                        progress['successful'],
                        progress['failed']
                    )
                except Exception:
                    pass
        
        # Filter out None results and ensure we have all results
        all_results = [r for r in all_results if r is not None]
        
        overall_end = datetime.now()
        overall_duration = (overall_end - overall_start).total_seconds()
        
        successful = sum(1 for r in all_results if r.get('success', False))
        failed = len(all_results) - successful
        
        # Step 3: Calculate statistics
        successful_results = [r for r in all_results if r.get('success', False)]
        
        if not successful_results:
            # Collect error information for debugging
            error_samples = []
            status_codes = {}
            for r in all_results[:10]:  # Sample first 10 errors
                if r and not r.get('success', False):
                    error_msg = r.get('error', 'Unknown error')
                    status = r.get('status_code', 'N/A')
                    error_samples.append(f"Status {status}: {error_msg[:100]}")
                    status_codes[status] = status_codes.get(status, 0) + 1
            
            error_summary = f"All {concurrent_requests} downloads failed. "
            if status_codes:
                error_summary += f"Status codes: {dict(status_codes)}. "
            if error_samples:
                error_summary += f"Sample errors: {'; '.join(error_samples[:3])}"
            else:
                error_summary += "No error details available."
            
            raise RuntimeError(error_summary)
        
        latencies = sorted([r['total_time_ms'] for r in successful_results])
        
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p99_index = min(int(len(latencies) * 0.99), len(latencies) - 1)
        p99_latency = latencies[p99_index]
        min_latency = latencies[0]
        max_latency = latencies[-1]
        
        # Calculate throughput
        total_bytes = sum(r['response_size_bytes'] for r in successful_results)
        throughput_rps = round(successful / overall_duration, 2) if overall_duration > 0 else 0
        throughput_mbps = round((total_bytes * 8) / (overall_duration * 1_000_000), 2) if overall_duration > 0 else 0
        avg_file_size = round(total_bytes / successful, 0) if successful > 0 else 0
        
        # Build results object
        error_breakdown = {}
        for result in all_results:
            if not result.get('success', False):
                error_key = result.get('error', 'Unknown error')
                error_breakdown[error_key] = error_breakdown.get(error_key, 0) + 1
        
        results = {
            'test_configuration': {
                'api_base_url': base_url,
                'model_url': TINY_LLM_URL,
                'artifact_id': artifact_id,
                'total_requests': concurrent_requests,
                'concurrent_requests': concurrent_requests,
                'timeout_seconds': timeout_seconds,
                'test_timestamp': datetime.now().isoformat(),
                'note': 'Files are downloaded but not saved to disk (only measured for metrics)'
            },
            'black_box_metrics': {
                'throughput': {
                    'requests_per_second': throughput_rps,
                    'mbps': throughput_mbps,
                    'total_bytes_downloaded': total_bytes,
                    'total_downloaded_mb': round(total_bytes / (1024 * 1024), 2),
                    'average_file_size_bytes': avg_file_size,
                    'average_file_size_kb': round(avg_file_size / 1024, 2)
                },
                'latency': {
                    'mean_ms': round(mean_latency, 2),
                    'median_ms': round(median_latency, 2),
                    'p99_ms': round(p99_latency, 2),
                    'min_ms': round(min_latency, 2),
                    'max_ms': round(max_latency, 2),
                    'all_latencies_ms': latencies
                },
                'request_summary': {
                    'total_requests': concurrent_requests,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round((successful / concurrent_requests) * 100, 2),
                    'total_duration_seconds': round(overall_duration, 2)
                }
            },
            'white_box_metrics': {
                'note': 'Concurrent download test - white-box metrics will be expanded for system monitoring',
                'error_breakdown': error_breakdown
            },
            'request_details': all_results[:10]  # First 10 for reference
        }
        
        return results


if __name__ == "__main__":
    """Standalone execution - prints results to stdout as JSON"""
    import json
    
    def print_progress(completed: int, total: int, successful: int, failed: int):
        """Progress callback for standalone execution"""
        print(f"Progress: {completed}/{total} completed ({successful} successful, {failed} failed)", file=sys.stderr)
    
    try:
        results = asyncio.run(run_benchmark(progress_callback=print_progress))
        # Output JSON to stdout for subprocess compatibility
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        print("Benchmark interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

