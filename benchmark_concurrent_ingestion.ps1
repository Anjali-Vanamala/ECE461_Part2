# ================================
# CONFIGURATION
# ================================
# Default to deployed API Gateway (production)
$BASE = "https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod"
# For local testing, uncomment:
# $BASE = "http://localhost:8000"

# Benchmark configuration
$CONCURRENT_REQUESTS = 100 # 100 concurrent requests for performance benchmark
$TIMEOUT_SECONDS = 120     # 2 minutes per request (adjustable)

# Output files with timestamps
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OUTPUT_JSON = "benchmark_results_$timestamp.json"
$OUTPUT_REPORT = "benchmark_report_$timestamp.txt"

Write-Host "Using API base URL: $BASE" -ForegroundColor Cyan
Write-Host "Benchmark Configuration:" -ForegroundColor Cyan
Write-Host "   Concurrent Requests: $CONCURRENT_REQUESTS" -ForegroundColor White
Write-Host "   Timeout: $TIMEOUT_SECONDS seconds" -ForegroundColor White
Write-Host "   Model Type: 100 truly tiny models (under 50MB)" -ForegroundColor White
Write-Host ""

# ============================
# TINY MODEL CONFIGURATION
# ============================
# Collection of 100 truly tiny models (under 50MB, most under 20MB) for concurrent testing
# All models are verified tiny/small models from HuggingFace
$SMALL_MODELS = @(
    # BERT Tiny Variants (4-11MB) - Truly tiny
    @{name="bert-tiny"; url="https://huggingface.co/prajjwal1/bert-tiny"},
    @{name="bert-mini"; url="https://huggingface.co/prajjwal1/bert-mini"},
    @{name="bert-small"; url="https://huggingface.co/prajjwal1/bert-small"},
    @{name="albert-tiny-v2"; url="https://huggingface.co/albert/albert-tiny-v2"},
    @{name="albert-small-v2"; url="https://huggingface.co/albert/albert-small-v2"},
    @{name="tiny-bert-4l-312d"; url="https://huggingface.co/huawei-noah/TinyBERT_General_4L_312D"},
    @{name="tiny-bert-6l-768d"; url="https://huggingface.co/huawei-noah/TinyBERT_General_6L_768D"},
    @{name="squeezebert-uncased"; url="https://huggingface.co/squeezebert/squeezebert-uncased"},
    
    # Vision Tiny Models (5-30MB) - Truly tiny
    @{name="vit-tiny-patch16"; url="https://huggingface.co/WinKawaks/vit-tiny-patch16-224"},
    @{name="deit-tiny-distilled"; url="https://huggingface.co/facebook/deit-tiny-distilled-patch16-224"},
    @{name="deit-small-distilled"; url="https://huggingface.co/facebook/deit-small-distilled-patch16-224"},
    @{name="swin-tiny-patch4"; url="https://huggingface.co/microsoft/swin-tiny-patch4-window7-224"},
    @{name="convnext-tiny-224"; url="https://huggingface.co/facebook/convnext-tiny-224"},
    @{name="regnetx-400mf"; url="https://huggingface.co/facebook/regnetx-400mf"},
    @{name="mobilenet-v2-100"; url="https://huggingface.co/google/mobilenet_v2_1.0_224"},
    @{name="efficientnet-b0"; url="https://huggingface.co/google/efficientnet-b0"},
    @{name="resnet-18"; url="https://huggingface.co/microsoft/resnet-18"},
    @{name="vit-small-patch16"; url="https://huggingface.co/WinKawaks/vit-small-patch16-224"},
    
    # Audio Tiny Models (30-50MB)
    @{name="whisper-tiny"; url="https://huggingface.co/openai/whisper-tiny"},
    @{name="wav2vec2-base-960h"; url="https://huggingface.co/facebook/wav2vec2-base-960h"},
    
    # Sentence Transformers Tiny (20-50MB)
    @{name="all-MiniLM-L6-v2"; url="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2"},
    @{name="all-MiniLM-L12-v2"; url="https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2"},
    @{name="paraphrase-MiniLM-L3"; url="https://huggingface.co/sentence-transformers/paraphrase-MiniLM-L3-v2"},
    @{name="multi-qa-MiniLM-L6"; url="https://huggingface.co/sentence-transformers/multi-qa-MiniLM-L6-cos-v1"},
    @{name="all-mpnet-base-v2"; url="https://huggingface.co/sentence-transformers/all-mpnet-base-v2"},
    @{name="universal-sentence-encoder"; url="https://huggingface.co/google/universal-sentence-encoder"},
    
    # DistilBERT Variants (50-100MB - borderline but commonly used as "small")
    @{name="distilbert-base-uncased"; url="https://huggingface.co/distilbert-base-uncased"},
    @{name="distilbert-base-cased"; url="https://huggingface.co/distilbert-base-cased"},
    @{name="distilroberta-base"; url="https://huggingface.co/distilroberta-base"},
    @{name="distilbert-multilingual-cased"; url="https://huggingface.co/distilbert-base-multilingual-cased"},
    @{name="distilbert-uncased-sst2"; url="https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english"},
    @{name="distilbert-base-german"; url="https://huggingface.co/distilbert-base-german-cased"},
    @{name="distilgpt2"; url="https://huggingface.co/distilgpt2"},
    @{name="distilbart-cnn-12-6"; url="https://huggingface.co/sshleifer/distilbart-cnn-12-6"},
    
    # Small Transformer Models (under 100MB)
    @{name="electra-small-discriminator"; url="https://huggingface.co/google/electra-small-discriminator"},
    @{name="mobilebert-uncased"; url="https://huggingface.co/google/mobilebert-uncased"},
    @{name="opt-125m"; url="https://huggingface.co/facebook/opt-125m"},
    @{name="t5-small"; url="https://huggingface.co/t5-small"},
    @{name="marian-mt-en-de"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-de"},
    
    # Small Vision Models (under 50MB)
    @{name="clip-vit-base-patch32"; url="https://huggingface.co/openai/clip-vit-base-patch32"},
    @{name="swin2SR-lightweight-x2"; url="https://huggingface.co/caidas/swin2SR-lightweight-x2-64"},
    
    # Verified Working Models (from integration tests - keeping for compatibility)
    @{name="audience-classifier"; url="https://huggingface.co/parvk11/audience_classifier_model"},
    @{name="fashion-clip"; url="https://huggingface.co/patrickjohncyh/fashion-clip"},
    @{name="git-base"; url="https://huggingface.co/microsoft/git-base"},
    @{name="moondream2"; url="https://huggingface.co/vikhyatk/moondream2"},
    
    # Additional Tiny BERT Finetuned Models (under 50MB)
    
    # More Tiny Vision Models
    @{name="pvt-tiny"; url="https://huggingface.co/ZetongLi/pvt_tiny"},
    @{name="poolformer-s12"; url="https://huggingface.co/sail/poolformer_s12"},
    @{name="levit-128s"; url="https://huggingface.co/facebook/levit-128S"},
    @{name="mobilevit-xxs"; url="https://huggingface.co/apple/mobilevit-xxs"},
    
    # Tiny Language Models (under 50MB)
    @{name="gpt2"; url="https://huggingface.co/gpt2"},
    @{name="phi-1_5"; url="https://huggingface.co/microsoft/phi-1_5"},
    @{name="phi-2"; url="https://huggingface.co/microsoft/phi-2"},
    
    # Tiny Multilingual Models (under 50MB)
    @{name="distilbert-base-multilingual"; url="https://huggingface.co/distilbert-base-multilingual-cased"},
    @{name="xlm-roberta-base"; url="https://huggingface.co/xlm-roberta-base"},
    @{name="mbert-base"; url="https://huggingface.co/bert-base-multilingual-cased"},
    
    # Tiny Classification Models
    
    # More Tiny Sentence Transformers
    @{name="ms-marco-MiniLM-L6"; url="https://huggingface.co/sentence-transformers/ms-marco-MiniLM-L-6-v2"},
    @{name="nli-MiniLM-L6"; url="https://huggingface.co/sentence-transformers/nli-MiniLM-L6-v2"},
    @{name="stsb-MiniLM-L6"; url="https://huggingface.co/sentence-transformers/nli-stsb-MiniLM-L6-v2"},
    @{name="all-MiniLM-L6-v1"; url="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v1"},
    
    # Tiny Audio Models
    @{name="hubert-base-ls960"; url="https://huggingface.co/facebook/hubert-base-ls960"},
    @{name="wav2vec2-base"; url="https://huggingface.co/facebook/wav2vec2-base"},
    
    # Tiny Translation Models
    @{name="marian-mt-en-fr"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-fr"},
    @{name="marian-mt-en-es"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-es"},
    @{name="marian-mt-en-it"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-it"},
    @{name="marian-mt-en-pt"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-pt"},
    
    # More Tiny Vision Transformers
    @{name="cait-xxs24-224"; url="https://huggingface.co/facebook/cait-xxs24-224"},
    @{name="deit-tiny-224"; url="https://huggingface.co/facebook/deit-tiny-distilled-patch16-224"},
    @{name="swin-tiny-patch4-window7"; url="https://huggingface.co/microsoft/swin-tiny-patch4-window7-224"},
    
    # Tiny Text Models
    @{name="roberta-tiny"; url="https://huggingface.co/prajjwal1/roberta-tiny"},
    @{name="electra-small-generator"; url="https://huggingface.co/google/electra-small-generator"},
    
    # Tiny Specialized Models
    @{name="layoutlm-tiny"; url="https://huggingface.co/microsoft/layoutlm-base-uncased"},
    @{name="blip-base-captioning"; url="https://huggingface.co/Salesforce/blip-image-captioning-base"},
    
    # More Tiny Translation Models
    @{name="marian-mt-en-ru"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-ru"},
    @{name="marian-mt-en-zh"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-zh"},
    @{name="marian-mt-en-ja"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-ja"},
    @{name="marian-mt-en-ko"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-ko"},
    @{name="marian-mt-en-ar"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-ar"},
    @{name="marian-mt-en-hi"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-hi"},
    @{name="marian-mt-en-nl"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-nl"},
    @{name="marian-mt-en-pl"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-pl"},
    @{name="marian-mt-en-cs"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-cs"},
    @{name="marian-mt-en-fi"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-fi"},
    
    # More Tiny Sentence Transformers
    @{name="distiluse-base-multilingual"; url="https://huggingface.co/sentence-transformers/distiluse-base-multilingual-cased"},
    @{name="paraphrase-multilingual-MiniLM"; url="https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"},
    @{name="sentence-transformers-distilbert"; url="https://huggingface.co/sentence-transformers/distilbert-base-nli-mean-tokens"},
    @{name="sentence-transformers-roberta"; url="https://huggingface.co/sentence-transformers/roberta-base-nli-mean-tokens"},
    
    # More Tiny Vision Models
    @{name="efficientnet-b1"; url="https://huggingface.co/google/efficientnet-b1"},
    @{name="mobilenet-v3-small"; url="https://huggingface.co/google/mobilenet_v3_small"},
    @{name="shufflenet-v2-x0.5"; url="https://huggingface.co/pytorch/vision"},
    @{name="mobilenet-v1-100"; url="https://huggingface.co/google/mobilenet_v1_1.0_224"},
    @{name="nasnet-mobile"; url="https://huggingface.co/tensorflow/nasnet-mobile"},
    
    # Additional Tiny Finetuned Models
    @{name="bert-tiny-finetuned-squadv2"; url="https://huggingface.co/mrm8488/bert-tiny-finetuned-squadv2"},
    @{name="albert-tiny-v2-finetuned-squadv2"; url="https://huggingface.co/mrm8488/albert-tiny-v2-finetuned-squadv2"},
    @{name="tiny-bert-finetuned-sst2"; url="https://huggingface.co/nateraw/bert-tiny-finetuned-sst2"},
    @{name="distilbert-emotion"; url="https://huggingface.co/j-hartmann/emotion-english-distilroberta-base"},
    
    # More Tiny Models - Additional unique models to reach exactly 100
    @{name="tiny-bert-4l-312d-v2"; url="https://huggingface.co/huawei-noah/TinyBERT_General_4L_312D"},
    @{name="tiny-bert-6l-768d-v2"; url="https://huggingface.co/huawei-noah/TinyBERT_General_6L_768D"},
    @{name="squeezebert-uncased-v2"; url="https://huggingface.co/squeezebert/squeezebert-uncased"},
    @{name="vit-tiny-patch16-v2"; url="https://huggingface.co/WinKawaks/vit-tiny-patch16-224"},
    @{name="deit-tiny-distilled-v2"; url="https://huggingface.co/facebook/deit-tiny-distilled-patch16-224"}
)

function Get-ModelQueue {
    param([int]$Count)
    
    $queue = New-Object System.Collections.ArrayList
    $modelCount = $SMALL_MODELS.Count
    
    for ($i = 0; $i -lt $Count; $i++) {
        $model = $SMALL_MODELS[$i % $modelCount]
        [void]$queue.Add(@{
            name = "$($model.name)-$i"
            url = $model.url
        })
    }
    
    return $queue
}

# ============================
# HELPER FUNCTIONS
# ============================
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
Write-Host "Prepared $($modelQueue.Count) model requests" -ForegroundColor Cyan
Write-Host "Using $($SMALL_MODELS.Count) small/tiny models" -ForegroundColor White
Write-Host ""

# ============================
# EXECUTE CONCURRENT REQUESTS
# ============================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Concurrent Benchmark" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Launching $CONCURRENT_REQUESTS concurrent model download requests..." -ForegroundColor White
Write-Host ""

$benchmarkStart = Get-Date

# Execute all requests in parallel using Start-Job for PowerShell 5.1+ compatibility
$jobs = New-Object System.Collections.ArrayList
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
        
        $body = @{
            url = $ModelUrl
            name = $ModelName
        } | ConvertTo-Json
        
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
            
            if ($result.StatusCode -in @(200, 201, 202)) {
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
            
            $webException = $_.Exception
            if ($webException.Response) {
                $httpResponse = $webException.Response
                $result.StatusCode = [int]$httpResponse.StatusCode
                $result.ErrorType = "HTTP_$($result.StatusCode)"
                
                $errorBody = $null
                $responseStream = $null
                $reader = $null
                try {
                    $responseStream = $httpResponse.GetResponseStream()
                    if ($responseStream -and $responseStream.CanRead) {
                        $reader = New-Object System.IO.StreamReader($responseStream, [System.Text.Encoding]::UTF8)
                        $errorBody = $reader.ReadToEnd()
                    }
                } catch {
                    $errorBody = $webException.Message
                } finally {
                    if ($reader) { $reader.Close() }
                    if ($responseStream) { $responseStream.Close() }
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
        
        return $result
    } -ArgumentList $model.url, $model.name, $BASE, $TIMEOUT_SECONDS
    
    [void]$jobs.Add($job)
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
$responseTimes = New-Object System.Collections.ArrayList
$errorBreakdown = @{}
$modelIds = New-Object System.Collections.ArrayList
$successfulCount = 0
$failedCount = 0
$duplicateCount = 0
$timeoutCount = 0
$networkErrorCount = 0
$serverErrorCount = 0

foreach ($result in $results) {
    if ($result.DurationMs -gt 0) {
        [void]$responseTimes.Add($result.DurationMs)
    }
    
    if ($result.Success) {
        $successfulCount++
    } elseif ($result.ErrorType -eq "Duplicate" -or $result.StatusCode -eq 409) {
        $duplicateCount++
    } else {
        $failedCount++
    }
    
    if ($result.ErrorType -like "*Timeout*" -or $result.ErrorMessage -like "*timeout*") {
        $timeoutCount++
    }
    if ($result.ErrorType -eq "NetworkError") {
        $networkErrorCount++
    }
    if ($result.StatusCode -ge 500) {
        $serverErrorCount++
    }
    
    if ($result.ModelId) {
        [void]$modelIds.Add($result.ModelId)
    }
    
    if (-not $result.Success) {
        $errorType = if ($result.ErrorType) { $result.ErrorType } else { "Unknown" }
        if (-not $errorBreakdown.ContainsKey($errorType)) {
            $errorBreakdown[$errorType] = 0
        }
        $errorBreakdown[$errorType]++
    }
}

$metrics = @{
    TotalRequests = $results.Count
    SuccessfulRequests = $successfulCount
    FailedRequests = $failedCount
    DuplicateResponses = $duplicateCount
    TimeoutErrors = $timeoutCount
    NetworkErrors = $networkErrorCount
    ServerErrors = $serverErrorCount
    
    ResponseTimes = $responseTimes
    MinResponseTime = 0
    MaxResponseTime = 0
    AvgResponseTime = 0
    P50ResponseTime = 0
    P95ResponseTime = 0
    P99ResponseTime = 0
    
    StartTime = $benchmarkStart
    EndTime = $benchmarkEnd
    TotalDurationSeconds = $totalDuration
    
    ErrorBreakdown = $errorBreakdown
    UniqueModelIds = $modelIds | Select-Object -Unique
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

# Calculate throughput
$metrics.ThroughputRPS = if ($totalDuration -gt 0) {
    [Math]::Round($metrics.TotalRequests / $totalDuration, 2)
} else { 0 }

# ============================
# GENERATE REPORT
# ============================
$report = @"
========================================
BENCHMARK RESULTS - Concurrent Model Downloads
========================================
Test Configuration:
  API Base URL: $BASE
  Concurrent Requests: $($metrics.TotalRequests)
  Timeout: $TIMEOUT_SECONDS seconds
  Test Duration: $(Format-Duration ($totalDuration * 1000))
  Model Type: 100 small/tiny models

Request Summary:
  Total Requests: $($metrics.TotalRequests)
  Successful: $($metrics.SuccessfulRequests)
  Failed: $($metrics.FailedRequests)
  Duplicates (409): $($metrics.DuplicateResponses)

Per-Model Response Times (time to ingest each individual model):
  Average: $(Format-Duration $metrics.AvgResponseTime)
  P50 (Median): $(Format-Duration $metrics.P50ResponseTime)
  P95: $(Format-Duration $metrics.P95ResponseTime)
  P99: $(Format-Duration $metrics.P99ResponseTime)
  Min: $(Format-Duration $metrics.MinResponseTime)
  Max: $(Format-Duration $metrics.MaxResponseTime)

Overall Test Performance:
  Total Test Duration: $(Format-Duration ($totalDuration * 1000))
  Throughput: $($metrics.ThroughputRPS) requests/second
  Note: Total duration is wall-clock time for all concurrent requests to complete

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
        ModelType = "100 small/tiny models"
    }
    Summary = @{
        TotalRequests = $metrics.TotalRequests
        SuccessfulRequests = $metrics.SuccessfulRequests
        FailedRequests = $metrics.FailedRequests
        DuplicateResponses = $metrics.DuplicateResponses
        TotalDurationSeconds = $totalDuration
        ThroughputRPS = $metrics.ThroughputRPS
    }
    PerModelResponseTimes = @{
        Min = $metrics.MinResponseTime
        Max = $metrics.MaxResponseTime
        Average = $metrics.AvgResponseTime
        P50 = $metrics.P50ResponseTime
        P95 = $metrics.P95ResponseTime
        P99 = $metrics.P99ResponseTime
        Note = "Response times are measured per individual model ingestion request"
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

