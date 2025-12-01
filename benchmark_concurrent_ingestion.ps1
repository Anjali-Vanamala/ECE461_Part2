# ================================
# CONFIGURATION
# ================================
# Default to deployed API Gateway (production)
$BASE = "https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod"
# For local testing, uncomment:
# $BASE = "http://localhost:8000"

# Benchmark configuration
$CONCURRENT_REQUESTS = 100 # 100 concurrent requests for performance benchmark
$TIMEOUT_SECONDS = 120    # 2 minutes per request (adjustable)

# Output files with timestamps
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OUTPUT_JSON = "benchmark_results_$timestamp.json"
$OUTPUT_REPORT = "benchmark_report_$timestamp.txt"

Write-Host "Using API base URL: $BASE" -ForegroundColor Cyan
Write-Host "Benchmark Configuration:" -ForegroundColor Cyan
Write-Host "   Concurrent Requests: $CONCURRENT_REQUESTS" -ForegroundColor White
Write-Host "   Timeout: $TIMEOUT_SECONDS seconds" -ForegroundColor White
Write-Host "   Model Type: 100 small/tiny models" -ForegroundColor White
Write-Host ""

# ============================
# SMALL/TINY MODEL CONFIGURATION
# ============================
# Collection of 100 small/tiny models for concurrent testing
# "Tiny" refers to small model size, not an organization name
# First 5 models have been verified to work in integration tests
# Remaining models are common small/tiny models from HuggingFace
$SMALL_MODELS = @(
    # Verified working models (from integration tests)
    @{name="distilbert-base-uncased"; url="https://huggingface.co/distilbert-base-uncased-distilled-squad"},
    @{name="audience-classifier"; url="https://huggingface.co/parvk11/audience_classifier_model"},
    @{name="bert-base-uncased"; url="https://huggingface.co/google-bert/bert-base-uncased"},
    @{name="whisper-tiny"; url="https://huggingface.co/openai/whisper-tiny/tree/main"},
    @{name="vit-tiny"; url="https://huggingface.co/WinKawaks/vit-tiny-patch16-224"},
    
    # Additional verified models from integration tests
    @{name="fashion-clip"; url="https://huggingface.co/patrickjohncyh/fashion-clip"},
    @{name="git-base"; url="https://huggingface.co/microsoft/git-base"},
    @{name="moondream2"; url="https://huggingface.co/vikhyatk/moondream2"},
    @{name="swin2SR-lightweight"; url="https://huggingface.co/caidas/swin2SR-lightweight-x2-64"},
    
    # Common small BERT variants
    @{name="distilbert-base-cased"; url="https://huggingface.co/distilbert-base-cased"},
    @{name="distilroberta-base"; url="https://huggingface.co/distilroberta-base"},
    @{name="bert-base-cased"; url="https://huggingface.co/bert-base-cased"},
    @{name="bert-base-multilingual-cased"; url="https://huggingface.co/bert-base-multilingual-cased"},
    @{name="bert-base-multilingual-uncased"; url="https://huggingface.co/bert-base-multilingual-uncased"},
    
    # Small transformer models
    @{name="albert-base-v2"; url="https://huggingface.co/albert-base-v2"},
    @{name="electra-small"; url="https://huggingface.co/google/electra-small-discriminator"},
    @{name="mobilebert-uncased"; url="https://huggingface.co/google/mobilebert-uncased"},
    @{name="tiny-bert"; url="https://huggingface.co/huawei-noah/TinyBERT_General_4L_312D"},
    
    # Small GPT models
    @{name="gpt2"; url="https://huggingface.co/gpt2"},
    @{name="distilgpt2"; url="https://huggingface.co/distilgpt2"},
    
    # Small vision models
    @{name="vit-base-patch16-224"; url="https://huggingface.co/google/vit-base-patch16-224"},
    @{name="deit-tiny"; url="https://huggingface.co/facebook/deit-tiny-distilled-patch16-224"},
    @{name="resnet-18"; url="https://huggingface.co/microsoft/resnet-18"},
    @{name="efficientnet-b0"; url="https://huggingface.co/google/efficientnet-b0"},
    
    # Small audio models
    @{name="whisper-base"; url="https://huggingface.co/openai/whisper-base"},
    @{name="wav2vec2-base"; url="https://huggingface.co/facebook/wav2vec2-base"},
    @{name="hubert-base"; url="https://huggingface.co/facebook/hubert-base-ls960"},
    
    # Small multilingual models
    @{name="mbert-base"; url="https://huggingface.co/bert-base-multilingual-cased"},
    @{name="xlm-roberta-base"; url="https://huggingface.co/xlm-roberta-base"},
    @{name="distilbert-multilingual"; url="https://huggingface.co/distilbert-base-multilingual-cased"},
    
    # Small classification models
    @{name="distilbert-uncased-finetuned-sst-2"; url="https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english"},
    @{name="roberta-base"; url="https://huggingface.co/roberta-base"},
    
    # Small encoder models
    @{name="sentence-transformers-all-MiniLM-L6"; url="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2"},
    @{name="sentence-transformers-all-mpnet-base"; url="https://huggingface.co/sentence-transformers/all-mpnet-base-v2"},
    @{name="universal-sentence-encoder"; url="https://huggingface.co/google/universal-sentence-encoder"},
    
    # Small specialized models
    @{name="bert-tiny"; url="https://huggingface.co/prajjwal1/bert-tiny"},
    @{name="bert-mini"; url="https://huggingface.co/prajjwal1/bert-mini"},
    @{name="bert-small"; url="https://huggingface.co/prajjwal1/bert-small"},
    @{name="bert-medium"; url="https://huggingface.co/prajjwal1/bert-medium"},
    @{name="albert-tiny"; url="https://huggingface.co/albert/albert-tiny-v2"},
    @{name="albert-small"; url="https://huggingface.co/albert/albert-small-v2"},
    @{name="bert-uncased-squad2"; url="https://huggingface.co/deepset/bert-base-uncased-squad2"},
    @{name="roberta-base-squad2"; url="https://huggingface.co/deepset/roberta-base-squad2"},
    
    # Additional small models
    @{name="gpt2-medium"; url="https://huggingface.co/gpt2-medium"},
    @{name="bloom-560m"; url="https://huggingface.co/bigscience/bloom-560m"},
    @{name="opt-125m"; url="https://huggingface.co/facebook/opt-125m"},
    @{name="t5-small"; url="https://huggingface.co/t5-small"},
    @{name="t5-base"; url="https://huggingface.co/t5-base"},
    @{name="bart-base"; url="https://huggingface.co/facebook/bart-base"},
    @{name="distilbart-cnn"; url="https://huggingface.co/sshleifer/distilbart-cnn-12-6"},
    @{name="marian-base"; url="https://huggingface.co/Helsinki-NLP/opus-mt-en-de"},
    @{name="mbart-base"; url="https://huggingface.co/facebook/mbart-large-50"},
    
    # Vision transformers (small)
    @{name="vit-small"; url="https://huggingface.co/WinKawaks/vit-small-patch16-224"},
    @{name="deit-small"; url="https://huggingface.co/facebook/deit-small-distilled-patch16-224"},
    @{name="swin-tiny"; url="https://huggingface.co/microsoft/swin-tiny-patch4-window7-224"},
    @{name="convnext-tiny"; url="https://huggingface.co/facebook/convnext-tiny-224"},
    @{name="regnetx-400mf"; url="https://huggingface.co/facebook/regnetx-400mf"},
    
    # More small models
    @{name="clip-vit-base"; url="https://huggingface.co/openai/clip-vit-base-patch32"},
    @{name="blip-base"; url="https://huggingface.co/Salesforce/blip-image-captioning-base"},
    @{name="flava-base"; url="https://huggingface.co/facebook/flava-full"},
    @{name="layoutlm-base"; url="https://huggingface.co/microsoft/layoutlm-base-uncased"},
    @{name="layoutlmv2-base"; url="https://huggingface.co/microsoft/layoutlmv2-base-uncased"},
    
    # Additional small models
    @{name="bert-base-japanese"; url="https://huggingface.co/cl-tohoku/bert-base-japanese"},
    @{name="camembert-base"; url="https://huggingface.co/camembert-base"},
    @{name="dbmdz-bert-base"; url="https://huggingface.co/dbmdz/bert-base-german-cased"},
    @{name="bert-base-chinese"; url="https://huggingface.co/bert-base-chinese"},
    @{name="xlm-base"; url="https://huggingface.co/xlm-mlm-en-2048"},
    @{name="distilbert-base-german"; url="https://huggingface.co/distilbert-base-german-cased"},
    @{name="squeezebert"; url="https://huggingface.co/squeezebert/squeezebert-uncased"},
    @{name="tinybert-4l"; url="https://huggingface.co/huawei-noah/TinyBERT_General_4L_312D"},
    @{name="tinybert-6l"; url="https://huggingface.co/huawei-noah/TinyBERT_General_6L_768D"},
    
    # Additional multilingual models
    @{name="bertweet-base"; url="https://huggingface.co/vinai/bertweet-base"},
    @{name="phobert-base"; url="https://huggingface.co/vinai/phobert-base"},
    @{name="indobert-base"; url="https://huggingface.co/indobenchmark/indobert-base-p1"},
    @{name="bert-base-korean"; url="https://huggingface.co/klue/bert-base"},
    @{name="bert-base-thai"; url="https://huggingface.co/monologg/bert-base-thai"},
    @{name="bert-base-arabic"; url="https://huggingface.co/aubmindlab/bert-base-arabert"},
    @{name="bert-base-hebrew"; url="https://huggingface.co/onlplab/alephbert-base"},
    @{name="bert-base-turkish"; url="https://huggingface.co/dbmdz/bert-base-turkish-cased"},
    @{name="bert-base-russian"; url="https://huggingface.co/DeepPavlov/bert-base-ru-cased"},
    @{name="bert-base-spanish"; url="https://huggingface.co/dccuchile/bert-base-spanish-wwm-uncased"},
    
    # European language models
    @{name="roberta-base-openai"; url="https://huggingface.co/openai-community/roberta-base-openai-detector"},
    @{name="bert-base-dutch"; url="https://huggingface.co/wietsedv/bert-base-dutch-cased"},
    @{name="bert-base-french"; url="https://huggingface.co/dbmdz/bert-base-french-europeana-cased"},
    @{name="bert-base-italian"; url="https://huggingface.co/dbmdz/bert-base-italian-cased"},
    @{name="bert-base-portuguese"; url="https://huggingface.co/neuralmind/bert-base-portuguese-cased"},
    @{name="bert-base-polish"; url="https://huggingface.co/dkleczek/bert-base-polish-cased-v1"},
    @{name="bert-base-czech"; url="https://huggingface.co/ufal/robeczech-base"},
    @{name="bert-base-finnish"; url="https://huggingface.co/TurkuNLP/bert-base-finnish-cased-v1"},
    @{name="bert-base-swedish"; url="https://huggingface.co/KB/bert-base-swedish-cased"},
    
    # Asian language models
    @{name="bert-base-vietnamese"; url="https://huggingface.co/trituenhantaoio/bert-base-vietnamese-uncased"},
    @{name="bert-base-indonesian"; url="https://huggingface.co/cahya/bert-base-indonesian-522M"},
    @{name="bert-base-hindi"; url="https://huggingface.co/monsoon-nlp/hindi-bert"},
    @{name="bert-base-bengali"; url="https://huggingface.co/sagorsarker/bangla-bert-base"},
    @{name="bert-base-marathi"; url="https://huggingface.co/l3cube-pune/marathi-bert"},
    @{name="bert-base-gujarati"; url="https://huggingface.co/l3cube-pune/gujarati-bert"},
    @{name="bert-base-punjabi"; url="https://huggingface.co/l3cube-pune/punjabi-bert"},
    @{name="bert-base-kannada"; url="https://huggingface.co/l3cube-pune/kannada-bert"},
    @{name="bert-base-malayalam"; url="https://huggingface.co/l3cube-pune/malayalam-bert"},
    @{name="bert-base-odia"; url="https://huggingface.co/l3cube-pune/odia-bert"}
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

