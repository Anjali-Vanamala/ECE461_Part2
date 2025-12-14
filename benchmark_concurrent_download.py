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
from typing import Dict, List, Optional
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

# Output files with timestamps
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_JSON = f"benchmark_download_concurrent_{timestamp}.json"
# Note: Files are downloaded but not saved to disk (only measured for metrics)


class Colors:
    """ANSI color codes for terminal output"""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    RESET = '\033[0m'


def print_colored(message: str, color: str = Colors.WHITE):
    """Print colored message"""
    print(f"{color}{message}{Colors.RESET}")


async def find_tiny_llm_artifact_id(session: aiohttp.ClientSession) -> str:
    """Find Tiny-LLM artifact ID using regex search endpoint"""
    print_colored("Step 1: Finding Tiny-LLM artifact ID...", Colors.YELLOW)
    
    url = f"{BASE_URL}/artifact/byRegEx"
    payload = {"regex": "Tiny-LLM"}
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 404:
                print_colored("ERROR: Tiny-LLM not found in registry. Please ingest it first.", Colors.RED)
                print_colored(f"Ingest URL: {TINY_LLM_URL}", Colors.YELLOW)
                sys.exit(1)
            
            response.raise_for_status()
            artifacts = await response.json()
            
            if not artifacts:
                print_colored("ERROR: Tiny-LLM not found in registry. Please ingest it first.", Colors.RED)
                print_colored(f"Ingest URL: {TINY_LLM_URL}", Colors.YELLOW)
                sys.exit(1)
            
            # Filter to models only and get the first one
            tiny_llm = next((a for a in artifacts if a.get('type') == 'model'), None)
            
            if not tiny_llm:
                print_colored("ERROR: Tiny-LLM model not found in registry. Please ingest it first.", Colors.RED)
                print_colored(f"Ingest URL: {TINY_LLM_URL}", Colors.YELLOW)
                sys.exit(1)
            
            artifact_id = tiny_llm['id']
            print_colored(f"Found Tiny-LLM with ID: {artifact_id}", Colors.GREEN)
            return artifact_id
            
    except Exception as e:
        print_colored(f"ERROR: Failed to find artifact: {e}", Colors.RED)
        sys.exit(1)


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


async def run_benchmark():
    """Main benchmark function"""
    print_colored("=== Concurrent Download Benchmark ===", Colors.CYAN)
    print_colored(f"API Base URL: {BASE_URL}", Colors.WHITE)
    print_colored(f"Target Model: {TINY_LLM_URL}", Colors.WHITE)
    print_colored(f"Concurrent Requests: {CONCURRENT_REQUESTS}", Colors.WHITE)
    print_colored("Note: Files will be downloaded but not saved to disk (only measured for metrics)", Colors.GRAY)
    print()
    
    # Create aiohttp session with timeout
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    
    # SSL context using certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    connector = aiohttp.TCPConnector(
        limit=200,  # Allow up to 200 concurrent connections
        ssl=ssl_context
    )
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Step 1: Find artifact ID
        artifact_id = await find_tiny_llm_artifact_id(session)
        
        # Step 2: Perform concurrent downloads
        print()
        print_colored(f"Step 2: Performing {CONCURRENT_REQUESTS} concurrent downloads...", Colors.YELLOW)
        print_colored("This may take several minutes...", Colors.YELLOW)
        print()
        
        download_url = f"{BASE_URL}/artifacts/model/{artifact_id}/download"
        
        overall_start = datetime.now()
        
        # Create all download tasks
        tasks = [
            download_one(session, download_url, i, timeout)
            for i in range(1, CONCURRENT_REQUESTS + 1)
        ]
        
        # Run all downloads concurrently with progress tracking
        print_colored(f"Starting {CONCURRENT_REQUESTS} concurrent download requests...", Colors.CYAN)
        print_colored("All requests are running concurrently (no local concurrency limit)", Colors.GRAY)
        print()
        
        # Track progress (use a dict for thread-safe updates)
        all_results = [None] * CONCURRENT_REQUESTS
        progress = {'completed': 0, 'successful': 0, 'failed': 0}
        
        def print_progress():
            """Print current progress"""
            elapsed = (datetime.now() - overall_start).total_seconds()
            print_colored(
                f"  Progress: {progress['completed']}/{CONCURRENT_REQUESTS} completed "
                f"({progress['successful']} successful, {progress['failed']} failed) | "
                f"Elapsed: {elapsed:.1f}s",
                Colors.CYAN
            )
        
        async def progress_reporter():
            """Background task to print progress updates every 2 seconds"""
            while progress['completed'] < CONCURRENT_REQUESTS:
                await asyncio.sleep(2.0)
                if progress['completed'] < CONCURRENT_REQUESTS:
                    print_progress()
        
        # Use asyncio.as_completed to track progress as tasks finish
        print_colored("Downloading... (updates every 2 seconds)", Colors.GRAY)
        
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
                    
                    # Progress is printed by background task every 2 seconds
                    # Only print final completion message
                    if progress['completed'] == CONCURRENT_REQUESTS:
                        print_progress()
                        
                except Exception as e:
                    # Handle unexpected exceptions (shouldn't happen, but safety net)
                    progress['completed'] += 1
                    progress['failed'] += 1
                    print_colored(f"  Unexpected error: {e}", Colors.RED)
        finally:
            # Cancel progress reporter when done
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
        
        # Filter out None results and ensure we have all results
        all_results = [r for r in all_results if r is not None]
        
        # Ensure we have exactly CONCURRENT_REQUESTS results
        if len(all_results) < CONCURRENT_REQUESTS:
            print_colored(
                f"WARNING: Only got {len(all_results)} results, expected {CONCURRENT_REQUESTS}",
                Colors.YELLOW
            )
        
        overall_end = datetime.now()
        overall_duration = (overall_end - overall_start).total_seconds()
        
        print()  # Final newline after progress updates
        print_colored("All downloads completed!", Colors.GREEN)
        
        successful = sum(1 for r in all_results if r.get('success', False))
        failed = len(all_results) - successful
        print_colored(f"  Successful: {successful}", Colors.WHITE)
        print_colored(f"  Failed: {failed}", Colors.RED if failed > 0 else Colors.WHITE)
        print_colored(f"  Total duration: {round(overall_duration, 2)} seconds", Colors.WHITE)
        
        # Step 3: Calculate statistics
        print()
        print_colored("Step 3: Calculating statistics...", Colors.YELLOW)
        
        successful_results = [r for r in all_results if r.get('success', False)]
        
        if not successful_results:
            print_colored("ERROR: No successful downloads. Cannot calculate statistics.", Colors.RED)
            sys.exit(1)
        
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
        throughput_mbps = round((total_bytes * 8) / (overall_duration * 1000000), 2) if overall_duration > 0 else 0
        avg_file_size = round(total_bytes / successful, 0) if successful > 0 else 0
        
        # Build results object
        error_breakdown = {}
        for result in all_results:
            if not result.get('success', False):
                error_key = result.get('error', 'Unknown error')
                error_breakdown[error_key] = error_breakdown.get(error_key, 0) + 1
        
        results = {
            'test_configuration': {
                'api_base_url': BASE_URL,
                'model_url': TINY_LLM_URL,
                'artifact_id': artifact_id,
                'total_requests': CONCURRENT_REQUESTS,
                'concurrent_requests': CONCURRENT_REQUESTS,
                'timeout_seconds': TIMEOUT_SECONDS,
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
                    'total_requests': CONCURRENT_REQUESTS,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round((successful / CONCURRENT_REQUESTS) * 100, 2),
                    'total_duration_seconds': round(overall_duration, 2)
                }
            },
            'white_box_metrics': {
                'note': 'Concurrent download test - white-box metrics will be expanded for system monitoring',
                'error_breakdown': error_breakdown
            },
            'request_details': all_results[:10]  # First 10 for reference
        }
        
        # Step 4: Output results
        print()
        print_colored("=== Results ===", Colors.CYAN)
        print_colored("Request Summary:", Colors.WHITE)
        print_colored(f"  Total Requests: {CONCURRENT_REQUESTS}", Colors.WHITE)
        print_colored(f"  Successful: {successful}", Colors.GREEN)
        print_colored(f"  Failed: {failed}", Colors.RED if failed > 0 else Colors.GRAY)
        print_colored(f"  Success Rate: {round((successful / CONCURRENT_REQUESTS) * 100, 2)}%", Colors.WHITE)
        print_colored(f"  Total Duration: {round(overall_duration, 2)} seconds", Colors.WHITE)
        print()
        print_colored("Throughput:", Colors.WHITE)
        print_colored(f"  Requests/Second: {throughput_rps}", Colors.WHITE)
        print_colored(f"  Throughput: {throughput_mbps} Mbps", Colors.WHITE)
        print_colored(f"  Total Downloaded: {round(total_bytes / (1024 * 1024), 2)} MB", Colors.WHITE)
        print_colored(f"  Average File Size: {round(avg_file_size / 1024, 2)} KB", Colors.WHITE)
        print()
        print_colored("Latency (ms):", Colors.WHITE)
        print_colored(f"  Mean:   {round(mean_latency, 2)}", Colors.WHITE)
        print_colored(f"  Median: {round(median_latency, 2)}", Colors.WHITE)
        print_colored(f"  P99:    {round(p99_latency, 2)}", Colors.WHITE)
        print_colored(f"  Min:    {round(min_latency, 2)}", Colors.WHITE)
        print_colored(f"  Max:    {round(max_latency, 2)}", Colors.WHITE)
        print()
        
        # Save to JSON
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print_colored(f"Results saved to: {OUTPUT_JSON}", Colors.GREEN)
        print_colored("Note: Downloaded files were not saved to disk (only measured for metrics)", Colors.GRAY)
        print()


if __name__ == "__main__":
    try:
        asyncio.run(run_benchmark())
    except KeyboardInterrupt:
        print_colored("\nBenchmark interrupted by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\nERROR: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)

