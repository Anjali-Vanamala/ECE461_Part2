# ================================
# CONFIGURATION
# ================================
# Default to deployed API Gateway (production)
$BASE = "https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod"
# For local testing, uncomment:
# $BASE = "http://localhost:8000"

# Benchmark configuration
$CONCURRENT_REQUESTS = 1  # Start with 5, scale to 100 later
$TIMEOUT_SECONDS = 120    # 2 minutes per request (adjustable)

# Output files with timestamps
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OUTPUT_JSON = "benchmark_results_$timestamp.json"
$OUTPUT_REPORT = "benchmark_report_$timestamp.txt"

Write-Host "Using API base URL: $BASE" -ForegroundColor Cyan
Write-Host "Benchmark Configuration:" -ForegroundColor Cyan
Write-Host "   Concurrent Requests: $CONCURRENT_REQUESTS" -ForegroundColor White
Write-Host "   Timeout: $TIMEOUT_SECONDS seconds" -ForegroundColor White
Write-Host "   Model Type: Tiny-LLM only" -ForegroundColor White
Write-Host ""

# ============================
# TINY-LLM MODEL CONFIGURATION
# ============================
# Collection of 5 different TinyLlama models for concurrent testing
$TINYLLM_MODELS = @(
    @{name="TinyLlama-1.1B-Chat"; url="https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0"},
    @{name="TinyLlama-1.1B-Intermediate"; url="https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"},
    @{name="TinyLlama-1.1B-Step50k"; url="https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-50k-1T"},
    @{name="TinyLlama-1.1B-Step100k"; url="https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-100k-1T"},
    @{name="TinyLlama-1.1B-Step200k"; url="https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-200k-1T"}
)

function Get-ModelQueue {
    param([int]$Count)
    
    $queue = @()
    
    # Use different TinyLlama models, cycling through the list if Count > available models
    for ($i = 0; $i -lt $Count; $i++) {
        $model = $TINYLLM_MODELS[$i % $TINYLLM_MODELS.Count]
        $queue += @{
            name = "$($model.name)-$i"
            url = $model.url
        }
    }
    
    return $queue
}

# ============================
# HELPER FUNCTIONS
# ============================
function Invoke-IngestRequest {
    param(
        [string]$ModelUrl,
        [string]$ModelName,
        [string]$BaseUrl,
        [int]$TimeoutSeconds
    )
    
    $result = @{
        ModelName = $ModelName
        ModelUrl = $ModelUrl
        StartTime = Get-Date
        EndTime = $null
        DurationMs = 0
        StatusCode = $null
        Success = $false
        ErrorType = $null
        ErrorMessage = $null
        ResponseBody = $null
        ModelId = $null
    }
    
    try {
        $body = @{
            url = $ModelUrl
            name = $ModelName
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest `
            -Uri "$BaseUrl/artifact/model" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec $TimeoutSeconds `
            -ErrorAction Stop
        
        $result.StatusCode = $response.StatusCode
        $result.EndTime = Get-Date
        $result.DurationMs = ($result.EndTime - $result.StartTime).TotalMilliseconds
        
        if ($response.Content) {
            try {
                $json = $response.Content | ConvertFrom-Json
                $result.ResponseBody = $json
                $result.ModelId = $json.metadata.id
            } catch {
                $result.ResponseBody = $response.Content
            }
        }
        
        # Success if 200 or 201
        if ($result.StatusCode -in @(200, 201)) {
            $result.Success = $true
        } elseif ($result.StatusCode -eq 409) {
            $result.ErrorType = "Duplicate"
        } else {
            $result.ErrorType = "HTTP_$($result.StatusCode)"
        }
        
    } catch [System.Net.WebException] {
        $result.EndTime = Get-Date
        $result.DurationMs = ($result.EndTime - $result.StartTime).TotalMilliseconds
        
        if ($_.Exception.Response) {
            $result.StatusCode = [int]$_.Exception.Response.StatusCode
            $result.ErrorType = "HTTP_$($result.StatusCode)"
            
            # Try to read error body
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $reader = New-Object IO.StreamReader($stream)
                $errorBody = $reader.ReadToEnd()
                $result.ErrorMessage = $errorBody
                try {
                    $result.ResponseBody = $errorBody | ConvertFrom-Json
                } catch {}
            } catch {}
        } else {
            $result.ErrorType = "NetworkError"
            $result.ErrorMessage = $_.Exception.Message
        }
        
    } catch [Microsoft.PowerShell.Commands.HttpResponseException] {
        $result.EndTime = Get-Date
        $result.DurationMs = ($result.EndTime - $result.StartTime).TotalMilliseconds
        $result.StatusCode = $_.Exception.Response.StatusCode.value__
        $result.ErrorType = "HTTP_$($result.StatusCode)"
        $result.ErrorMessage = $_.Exception.Message
        
    } catch {
        $result.EndTime = Get-Date
        $result.DurationMs = ($result.EndTime - $result.StartTime).TotalMilliseconds
        $result.ErrorType = "UnknownError"
        $result.ErrorMessage = $_.Exception.Message
    }
    
    return $result
}

function Get-Percentile {
    param(
        [double[]]$Values,
        [double]$Percentile
    )
    
    if ($Values.Count -eq 0) { return 0 }
    
    $sorted = $Values | Sort-Object
    $index = [Math]::Ceiling(($sorted.Count - 1) * ($Percentile / 100))
    if ($index -ge $sorted.Count) { $index = $sorted.Count - 1 }
    
    return $sorted[$index]
}

function Format-Duration {
    param([double]$Milliseconds)
    
    if ($Milliseconds -lt 1000) {
        return "$([Math]::Round($Milliseconds, 1))ms"
    } elseif ($Milliseconds -lt 60000) {
        return "$([Math]::Round($Milliseconds / 1000, 1))s"
    } else {
        $seconds = [Math]::Round($Milliseconds / 1000, 1)
        $minutes = [Math]::Floor($seconds / 60)
        $secs = [Math]::Round($seconds % 60, 1)
        return "${minutes}m ${secs}s"
    }
}

# ============================
# PRE-BENCHMARK SETUP
# ============================
Write-Host "Resetting registry..." -ForegroundColor Yellow
try {
    $resetResponse = Invoke-WebRequest -Uri "$BASE/reset" -Method Delete -TimeoutSec 30
    if ($resetResponse.StatusCode -eq 200) {
        Write-Host "Registry reset complete" -ForegroundColor Green
    }
} catch {
    Write-Host "Warning: Could not reset registry: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "Health check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BASE/health" -Method Get -TimeoutSec 10
    if ($health.status -eq "healthy") {
        Write-Host "Backend is healthy" -ForegroundColor Green
    } else {
        Write-Host "Warning: Backend health status: $($health.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error: Backend health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Continuing anyway..." -ForegroundColor Yellow
}

Write-Host ""

# ============================
# PREPARE MODEL QUEUE
# ============================
$modelQueue = Get-ModelQueue -Count $CONCURRENT_REQUESTS
Write-Host "Prepared $($modelQueue.Count) Tiny-LLM model requests" -ForegroundColor Cyan
Write-Host "Using $($TINYLLM_MODELS.Count) different TinyLlama models" -ForegroundColor White
Write-Host ""

# ============================
# EXECUTE CONCURRENT REQUESTS
# ============================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Concurrent Benchmark" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Launching $CONCURRENT_REQUESTS concurrent Tiny-LLM download requests..." -ForegroundColor White
Write-Host ""

$benchmarkStart = Get-Date

# Execute all requests in parallel using Start-Job for PowerShell 5.1+ compatibility
$jobs = @()
foreach ($model in $modelQueue) {
    $job = Start-Job -ScriptBlock {
        param($ModelUrl, $ModelName, $BaseUrl, $TimeoutSeconds)
        
        $startTime = Get-Date
        $result = @{
            ModelName = $ModelName
            ModelUrl = $ModelUrl
            StartTime = $startTime.ToString("o")
            EndTime = $null
            DurationMs = 0
            StatusCode = $null
            Success = $false
            ErrorType = $null
            ErrorMessage = $null
            ResponseBody = $null
            ModelId = $null
        }
        
        try {
            $body = @{
                url = $ModelUrl
                name = $ModelName
            } | ConvertTo-Json
            
            # Use Invoke-WebRequest with proper error handling
            try {
                $response = Invoke-WebRequest `
                    -Uri "$BaseUrl/artifact/model" `
                    -Method Post `
                    -ContentType "application/json" `
                    -Body $body `
                    -TimeoutSec $TimeoutSeconds `
                    -UseBasicParsing `
                    -ErrorAction Stop
                
                $endTime = Get-Date
                $result.EndTime = $endTime.ToString("o")
                $result.DurationMs = ($endTime - $startTime).TotalMilliseconds
                
                # Success case
                $result.StatusCode = $response.StatusCode
                
                if ($response.Content) {
                    try {
                        $json = $response.Content | ConvertFrom-Json
                        $result.ResponseBody = $json
                        if ($json.metadata -and $json.metadata.id) {
                            $result.ModelId = $json.metadata.id
                        }
                    } catch {
                        $result.ResponseBody = $response.Content
                    }
                }
                
                if ($result.StatusCode -in @(200, 201)) {
                    $result.Success = $true
                } elseif ($result.StatusCode -eq 409) {
                    $result.ErrorType = "Duplicate"
                } else {
                    $result.ErrorType = "HTTP_$($result.StatusCode)"
                }
                
            } catch [System.Net.WebException] {
                $endTime = Get-Date
                $result.EndTime = $endTime.ToString("o")
                $result.DurationMs = ($endTime - $startTime).TotalMilliseconds
                
                # Extract status code from WebException
                $webException = $_.Exception
                if ($webException.Response) {
                    $httpResponse = $webException.Response
                    $result.StatusCode = [int]$httpResponse.StatusCode
                    $result.ErrorType = "HTTP_$($result.StatusCode)"
                    
                    # Read error response body
                    $errorBody = $null
                    try {
                        $responseStream = $httpResponse.GetResponseStream()
                        if ($responseStream -and $responseStream.CanRead) {
                            $reader = New-Object System.IO.StreamReader($responseStream, [System.Text.Encoding]::UTF8)
                            $errorBody = $reader.ReadToEnd()
                            $reader.Close()
                            $responseStream.Close()
                        }
                    } catch {
                        # If stream reading fails, try to get info from exception
                        $errorBody = $webException.Message
                    }
                    
                    if ($errorBody -and $errorBody.Trim()) {
                        $result.ErrorMessage = $errorBody
                        try {
                            $parsed = $errorBody | ConvertFrom-Json
                            $result.ResponseBody = $parsed
                            if ($parsed.detail) {
                                $result.ErrorMessage = $parsed.detail
                            } elseif ($parsed.message) {
                                $result.ErrorMessage = $parsed.message
                            }
                        } catch {
                            $result.ResponseBody = $errorBody
                        }
                    } else {
                        $result.ErrorMessage = "Empty response body. Status: $($result.StatusCode). Exception: $($webException.Message)"
                    }
                } else {
                    $result.StatusCode = 0
                    $result.ErrorType = "NetworkError"
                    $result.ErrorMessage = $webException.Message
                }
                
            } catch {
                $endTime = Get-Date
                $result.EndTime = $endTime.ToString("o")
                $result.DurationMs = ($endTime - $startTime).TotalMilliseconds
                $result.ErrorType = "Exception"
                $result.ErrorMessage = $_.Exception.ToString()
            }
            
        } catch {
            $endTime = Get-Date
            $result.EndTime = $endTime.ToString("o")
            $result.DurationMs = ($endTime - $startTime).TotalMilliseconds
            $result.ErrorType = "Exception"
            $result.ErrorMessage = $_.Exception.ToString()
        }
        
        return $result
    } -ArgumentList $model.url, $model.name, $BASE, $TIMEOUT_SECONDS
    
    $jobs += $job
}

# Wait for all jobs to complete and collect results
$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$benchmarkEnd = Get-Date
$totalDuration = ($benchmarkEnd - $benchmarkStart).TotalSeconds

Write-Host "All requests completed" -ForegroundColor Green
Write-Host ""

# ============================
# ANALYZE RESULTS
# ============================
$metrics = @{
    TotalRequests = $results.Count
    SuccessfulRequests = ($results | Where-Object { $_.Success }).Count
    FailedRequests = ($results | Where-Object { -not $_.Success -and $_.ErrorType -ne "Duplicate" }).Count
    DuplicateResponses = ($results | Where-Object { $_.ErrorType -eq "Duplicate" -or $_.StatusCode -eq 409 }).Count
    TimeoutErrors = ($results | Where-Object { $_.ErrorType -like "*Timeout*" -or $_.ErrorMessage -like "*timeout*" }).Count
    NetworkErrors = ($results | Where-Object { $_.ErrorType -eq "NetworkError" }).Count
    ServerErrors = ($results | Where-Object { $_.StatusCode -ge 500 }).Count
    
    ResponseTimes = ($results | Where-Object { $_.DurationMs -gt 0 } | ForEach-Object { $_.DurationMs })
    MinResponseTime = 0
    MaxResponseTime = 0
    AvgResponseTime = 0
    P50ResponseTime = 0
    P95ResponseTime = 0
    P99ResponseTime = 0
    
    StartTime = $benchmarkStart
    EndTime = $benchmarkEnd
    TotalDurationSeconds = $totalDuration
    
    ErrorBreakdown = @{}
    ModelIds = ($results | Where-Object { $_.ModelId } | ForEach-Object { $_.ModelId })
    UniqueModelIds = @()
}

# Calculate response time statistics
if ($metrics.ResponseTimes.Count -gt 0) {
    $metrics.MinResponseTime = ($metrics.ResponseTimes | Measure-Object -Minimum).Minimum
    $metrics.MaxResponseTime = ($metrics.ResponseTimes | Measure-Object -Maximum).Maximum
    $metrics.AvgResponseTime = ($metrics.ResponseTimes | Measure-Object -Average).Average
    $metrics.P50ResponseTime = Get-Percentile -Values $metrics.ResponseTimes -Percentile 50
    $metrics.P95ResponseTime = Get-Percentile -Values $metrics.ResponseTimes -Percentile 95
    $metrics.P99ResponseTime = Get-Percentile -Values $metrics.ResponseTimes -Percentile 99
}

# Count unique model IDs
$metrics.UniqueModelIds = $metrics.ModelIds | Select-Object -Unique

# Error breakdown by type
$results | Where-Object { -not $_.Success } | ForEach-Object {
    $errorType = if ($_.ErrorType) { $_.ErrorType } else { "Unknown" }
    if (-not $metrics.ErrorBreakdown.ContainsKey($errorType)) {
        $metrics.ErrorBreakdown[$errorType] = 0
    }
    $metrics.ErrorBreakdown[$errorType]++
}

# Calculate throughput
$metrics.ThroughputRPS = if ($totalDuration -gt 0) {
    [Math]::Round($metrics.TotalRequests / $totalDuration, 2)
} else { 0 }

# ============================
# GENERATE REPORT
# ============================
$report = @"
========================================
BENCHMARK RESULTS - Tiny-LLM Downloads
========================================
Test Configuration:
  API Base URL: $BASE
  Concurrent Requests: $($metrics.TotalRequests)
  Timeout: $TIMEOUT_SECONDS seconds
  Test Duration: $(Format-Duration ($totalDuration * 1000))
  Model Type: Tiny-LLM only

Request Summary:
  Total Requests: $($metrics.TotalRequests)
  Successful: $($metrics.SuccessfulRequests)
  Failed: $($metrics.FailedRequests)
  Duplicates (409): $($metrics.DuplicateResponses)

Response Times:
  Average: $(Format-Duration $metrics.AvgResponseTime)
  P50 (Median): $(Format-Duration $metrics.P50ResponseTime)
  P95: $(Format-Duration $metrics.P95ResponseTime)
  P99: $(Format-Duration $metrics.P99ResponseTime)
  Min: $(Format-Duration $metrics.MinResponseTime)
  Max: $(Format-Duration $metrics.MaxResponseTime)

Performance:
  Total Duration: $(Format-Duration ($totalDuration * 1000))
  Throughput: $($metrics.ThroughputRPS) requests/second

Error Breakdown:
"@

foreach ($errorType in $metrics.ErrorBreakdown.Keys | Sort-Object) {
    $count = $metrics.ErrorBreakdown[$errorType]
    $report += "`n  $errorType : $count"
}

$report += @"

Unique Models Ingested: $($metrics.UniqueModelIds.Count)
Model IDs: $($metrics.UniqueModelIds -join ', ')

========================================
"@

# Display report
Write-Host $report -ForegroundColor White

# Save JSON results
$jsonOutput = @{
    Configuration = @{
        BaseUrl = $BASE
        ConcurrentRequests = $CONCURRENT_REQUESTS
        TimeoutSeconds = $TIMEOUT_SECONDS
        ModelType = "Tiny-LLM"
    }
    Summary = @{
        TotalRequests = $metrics.TotalRequests
        SuccessfulRequests = $metrics.SuccessfulRequests
        FailedRequests = $metrics.FailedRequests
        DuplicateResponses = $metrics.DuplicateResponses
        TotalDurationSeconds = $totalDuration
        ThroughputRPS = $metrics.ThroughputRPS
    }
    ResponseTimes = @{
        Min = $metrics.MinResponseTime
        Max = $metrics.MaxResponseTime
        Average = $metrics.AvgResponseTime
        P50 = $metrics.P50ResponseTime
        P95 = $metrics.P95ResponseTime
        P99 = $metrics.P99ResponseTime
    }
    Errors = $metrics.ErrorBreakdown
    ModelIds = $metrics.UniqueModelIds
    Results = $results
}

$jsonOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $OUTPUT_JSON -Encoding UTF8

# Save text report
$report | Out-File -FilePath $OUTPUT_REPORT -Encoding UTF8

Write-Host ""
Write-Host "Results saved:" -ForegroundColor Green
Write-Host "   JSON: $OUTPUT_JSON" -ForegroundColor White
Write-Host "   Report: $OUTPUT_REPORT" -ForegroundColor White
Write-Host ""

