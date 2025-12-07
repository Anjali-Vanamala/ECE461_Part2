# ================================
# CONFIG: Change your backend URL
# ================================
$BASE = "http://localhost:8000"
# Example for cloud deployment:
# $BASE = "https://my-artifact-service.cloudprovider.com"

Write-Host "🔥 Using API base URL: $BASE" -ForegroundColor Cyan

# ============================
# HELPER FUNCTION
# ============================
function Test-Call {
    param(
        [string]$Label,
        [scriptblock]$Script,
        [int[]]$ExpectedStatus = @(200),
        [scriptblock]$Assert = $null
    )

    Write-Host "`n===============================" -ForegroundColor DarkGray
    Write-Host "▶ $Label" -ForegroundColor Yellow
    Write-Host "-------------------------------" -ForegroundColor DarkGray

    try {
        $resp = $null
        $actualStatus = $null
        $json = $null

        try {
            # Normal (2xx) response
            $resp = & $Script

            # Extract status code for success cases
            $actualStatus = $resp.StatusCode
            if (-not $actualStatus) {
                $actualStatus = $resp.RawContent.Split(" ")[1] -as [int]
            }

            if ($resp.Content) {
                try { $json = $resp.Content | ConvertFrom-Json } catch {}
            }
        }
        catch [System.Net.WebException] {
            # Non-2xx (error) responses arrive here
            $response = $_.Exception.Response
            $actualStatus = [int]$response.StatusCode

            # Read error body JSON
            try {
                $stream = $response.GetResponseStream()
                $reader = New-Object IO.StreamReader($stream)
                $body = $reader.ReadToEnd()
                $json = $body | ConvertFrom-Json
            } catch {
                $json = $null
            }
        }

        # Validate expected status
        if ($actualStatus -notin $ExpectedStatus) {
            throw "Expected HTTP $($ExpectedStatus -join ', ') but got $actualStatus"
        }

        # Run extra assertions if provided
        if ($Assert) {
            & $Assert $json $actualStatus
        }

        Write-Host "✓ PASS: $Label" -ForegroundColor Green
        if ($json) { $json | ConvertTo-Json -Depth 20 }
        return $json
    }
    catch {
        Write-Host "✗ FAIL: $Label" -ForegroundColor Red
        throw
    }
}




# ====================================
# === DELETE /reset ===
# ====================================
Test-Call "DELETE /reset" {
    Invoke-WebRequest -Uri "$BASE/reset" -Method Delete
} -ExpectedStatus @(200) -Assert {
    param($json)

    if ($json.status -ne "reset") {
        throw "Expected JSON.status = 'reset' but got '$($json.status)'"
    }
}

# ====================================
# === GET /tracks ===
# ====================================
Test-Call "GET /tracks" {
    Invoke-WebRequest -Uri "$BASE/tracks" -Method Get
} -ExpectedStatus @(200)

# ====================================
# === GET /health ===
# ====================================
Test-Call "GET /health" {
    Invoke-WebRequest -Uri "$BASE/health" -Method Get
} -ExpectedStatus @(200)

# ====================================
# === POST /artifact/model (distilbert-base-uncased-distilled-squad) ===
# ====================================
$resp_distilbert = Test-Call "POST /artifact/model distilbert-base-uncased-distilled-squad" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"distilbert-base-uncased-distilled-squad","url":"https://huggingface.co/distilbert-base-uncased-distilled-squad"}'
} -ExpectedStatus @(200, 201, 202)

$distilbertModelId = $resp_distilbert.metadata.id

# ====================================
# === POST /artifact/model (audience_classifier_model) ===
# ====================================
$resp_audience = Test-Call "POST /artifact/model audience_classifier_model" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"audience_classifier_model","url":"https://huggingface.co/parvk11/audience_classifier_model"}'
} -ExpectedStatus @(200, 201, 202)
$audienceClassifierModelId = $resp_audience.metadata.id

# ====================================
# === POST /artifact/model (bert-base-uncased) ===
# ====================================
$resp_bert = Test-Call "POST /artifact/model bert-base-uncased" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"bert-base-uncased","url":"https://huggingface.co/google-bert/bert-base-uncased"}'
} -ExpectedStatus @(200, 201, 202)
$bertBaseId = $resp_bert.metadata.id

# ====================================
# === POST /artifact/model (bert-base-uncased duplicate) ===
# ====================================
Test-Call "POST /artifact/model bert-base-uncased (duplicate)" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"bert-base-uncased","url":"https://huggingface.co/google-bert/bert-base-uncased"}'
} -ExpectedStatus @(409)

# ====================================
# === POST /artifact/code (google-research-bert) ===
# ====================================
$resp_googleBert = Test-Call "POST /artifact/code google-research-bert" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"google-research-bert","url":"https://github.com/google-research/bert"}'
} -ExpectedStatus @(200, 201)
$googleResearchBertCodeId = $resp_googleBert.metadata.id

# ====================================
# === POST /artifact/dataset (bookcorpus) ===
# ====================================
$resp_bookcorpus = Test-Call "POST /artifact/dataset bookcorpus" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/dataset" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"bookcorpus","url":"https://huggingface.co/datasets/bookcorpus/bookcorpus"}'
} -ExpectedStatus @(200, 201)
$bookcorpusDatasetId = $resp_bookcorpus.metadata.id

# ====================================
# === POST /artifact/model (patrickjohncyh-fashion-clip) ===
# ====================================
$resp_patrickClip = Test-Call "POST /artifact/model patrickjohncyh-fashion-clip" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"patrickjohncyh-fashion-clip","url":"https://huggingface.co/patrickjohncyh/fashion-clip"}'
} -ExpectedStatus @(200, 201, 202)
$patrickFashionClipModelId = $resp_patrickClip.metadata.id

# ====================================
# === POST /artifact/model (WinKawaks-vit-tiny-patch16-224) ===
# ====================================
$resp_winKawaks = Test-Call "POST /artifact/model WinKawaks-vit-tiny-patch16-224" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"WinKawaks-vit-tiny-patch16-224","url":"https://huggingface.co/WinKawaks/vit-tiny-patch16-224"}'
} -ExpectedStatus @(200, 201, 202)
$winKawaksVitModelId = $resp_winKawaks.metadata.id

# ====================================
# === POST /artifact/model (microsoft-git-base) ===
# ====================================
$resp_msGitBase = Test-Call "POST /artifact/model microsoft-git-base" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"microsoft-git-base","url":"https://huggingface.co/microsoft/git-base"}'
} -ExpectedStatus @(200, 201, 202)
$microsoftGitBaseModelId = $resp_msGitBase.metadata.id

# ====================================
# === POST /artifact/model (vikhyatk-moondream2) ===
# ====================================
$resp_moondream2 = Test-Call "POST /artifact/model vikhyatk-moondream2" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"vikhyatk-moondream2","url":"https://huggingface.co/vikhyatk/moondream2"}'
} -ExpectedStatus @(200, 201, 202)
$vikhyatMoondream2ModelId = $resp_moondream2.metadata.id

# ====================================
# === POST /artifact/model (caidas-swin2SR-lightweight-x2-64) ===
# ====================================
$resp_swin2 = Test-Call "POST /artifact/model caidas-swin2SR-lightweight-x2-64" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"caidas-swin2SR-lightweight-x2-64","url":"https://huggingface.co/caidas/swin2SR-lightweight-x2-64"}'
} -ExpectedStatus @(200, 201, 202)
$caidasSwin2ModelId = $resp_swin2.metadata.id

# ====================================
# === POST /artifact/code (ptm-recommendation-with-transformers) ===
# ====================================
$resp_ptm = Test-Call "POST /artifact/code ptm-recommendation-with-transformers" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"ptm-recommendation-with-transformers","url":"https://github.com/Parth1811/ptm-recommendation-with-transformers.git"}'
} -ExpectedStatus @(200, 201)
$ptmRecommendationCodeId = $resp_ptm.metadata.id

# ====================================
# === POST /artifact/code (lerobot) ===
# ====================================
$resp_lerobotCode = Test-Call "POST /artifact/code lerobot" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"lerobot","url":"https://github.com/huggingface/lerobot/tree/main"}'
} -ExpectedStatus @(200, 201)
$lerobotCodeId = $resp_lerobotCode.metadata.id

# ====================================
# === POST /artifact/code (fashion-clip) ===
# ====================================
$resp_fashionClipCode = Test-Call "POST /artifact/code fashion-clip" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"fashion-clip","url":"https://github.com/patrickjohncyh/fashion-clip"}'
} -ExpectedStatus @(200, 201)
$fashionClipCodeId = $resp_fashionClipCode.metadata.id

# ====================================
# === POST /artifact/code (microsoft-git) ===
# ====================================
$resp_msGitCode = Test-Call "POST /artifact/code microsoft-git" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"microsoft-git","url":"https://github.com/microsoft/git"}'
} -ExpectedStatus @(200, 201)
$microsoftGitCodeId = $resp_msGitCode.metadata.id

# ====================================
# === POST /artifact/code (moondream) ===
# ====================================
$resp_moondreamCode = Test-Call "POST /artifact/code moondream" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"moondream","url":"https://github.com/vikhyat/moondream"}'
} -ExpectedStatus @(200, 201)
$moondreamCodeId = $resp_moondreamCode.metadata.id

# ====================================
# === POST /artifact/code (mv-lab-swin2sr) ===
# ====================================
$resp_mvLab = Test-Call "POST /artifact/code mv-lab-swin2sr" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"mv-lab-swin2sr","url":"https://github.com/mv-lab/swin2sr"}'
} -ExpectedStatus @(200, 201)
$mvLabSwin2srCodeId = $resp_mvLab.metadata.id

# ====================================
# === POST /artifact/code (transformers-research-projects-distillation) ===
# ====================================
$resp_transformersDistill = Test-Call "POST /artifact/code transformers-research-projects-distillation" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"transformers-research-projects-distillation","url":"https://github.com/huggingface/transformers-research-projects/tree/main/distillation"}'
} -ExpectedStatus @(200, 201)
$transformersDistillationCodeId = $resp_transformersDistill.metadata.id

# -------------------------------
#  ARTIFACT CODE REGISTRATIONS
# -------------------------------

$resp_whisper = Test-Call "POST /artifact/code openai-whisper" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/code" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"openai-whisper","url":"https://github.com/openai/whisper"}'
} -ExpectedStatus @(200, 201)
$openaiWhisperCodeId = $resp_whisper.metadata.id

# -------------------------------
#  ARTIFACT DATASET REGISTRATIONS
# -------------------------------

$resp_lerobotPusht = Test-Call "POST /artifact/dataset lerobot-pusht" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/dataset" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"lerobot-pusht","url":"https://huggingface.co/datasets/lerobot/pusht"}'
} -ExpectedStatus @(200, 201)
$lerobotPushtDatasetId = $resp_lerobotPusht.metadata.id

$resp_fashionMnist = Test-Call "POST /artifact/dataset fashion-mnist" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/dataset" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"fashion-mnist","url":"https://github.com/zalandoresearch/fashion-mnist"}'
} -ExpectedStatus @(200, 201)
$fashionMnistDatasetId = $resp_fashionMnist.metadata.id

$resp_flickr = Test-Call "POST /artifact/dataset hliang001-flickr2k" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/dataset" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"hliang001-flickr2k","url":"https://www.kaggle.com/datasets/hliang001/flickr2k"}'
} -ExpectedStatus @(200, 201)
$hliangFlickr2kDatasetId = $resp_flickr.metadata.id

$resp_squad = Test-Call "POST /artifact/dataset rajpurkar-squad" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/dataset" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"rajpurkar-squad","url":"https://huggingface.co/datasets/rajpurkar/squad"}'
} -ExpectedStatus @(200, 201)
$rajpurkarSquadDatasetId = $resp_squad.metadata.id

# -------------------------------
#  ARTIFACT MODEL REGISTRATIONS
# -------------------------------

$resp_longNameModel = Test-Call "POST /artifact/model long aaaaa..." {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab","url":"https://huggingface.co/parthvpatil18/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"}'
} -ExpectedStatus @(200, 201, 202)
$longNameModelId = $resp_longNameModel.metadata.id

$resp_lerobotDiffusion = Test-Call "POST /artifact/model lerobot-diffusion_pusht" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/model" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"name":"lerobot-diffusion_pusht","url":"https://huggingface.co/lerobot/diffusion_pusht"}'
} -ExpectedStatus @(200, 201, 202)
$lerobotDiffusionModelId = $resp_lerobotDiffusion.metadata.id


# -------------------------------
#  REQUEST ALL MODELS
# -------------------------------

Test-Call 'POST /artifacts name="*", types=["model"]' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":["model"]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    $expectedNames = @(
        "distilbert-base-uncased-distilled-squad",
        "audience_classifier_model",
        "bert-base-uncased",
        "patrickjohncyh-fashion-clip",
        "WinKawaks-vit-tiny-patch16-224",
        "microsoft-git-base",
        "vikhyatk-moondream2",
        "caidas-swin2SR-lightweight-x2-64",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab",
        "lerobot-diffusion_pusht"
    )

    # Extract names properly — THIS is what was missing
    $returnedNames = $json | ForEach-Object { $_.name }

    # Order does not matter
    if (@(Compare-Object -ReferenceObject $expectedNames -DifferenceObject $returnedNames)) {
        throw "Returned artifact model list does not match expected set."
    }
}

# === POST /artifacts ({"name":"*","types":[]}) ===
Test-Call 'POST /artifacts name="*", types=[]' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    # Normalize objects (ignore IDs)
    function Normalize {
        param($item)
        return ([PSCustomObject]@{
            name = $item.name
            type = $item.type
        } | ConvertTo-Json -Compress)
    }

    $actualSet = $json | ForEach-Object { Normalize $_ }

    $expectedSet = @(
        @{ name="distilbert-base-uncased-distilled-squad"; type="model" }
        @{ name="audience_classifier_model"; type="model" }
        @{ name="bert-base-uncased"; type="model" }
        @{ name="patrickjohncyh-fashion-clip"; type="model" }
        @{ name="WinKawaks-vit-tiny-patch16-224"; type="model" }
        @{ name="microsoft-git-base"; type="model" }
        @{ name="vikhyatk-moondream2"; type="model" }
        @{ name="caidas-swin2SR-lightweight-x2-64"; type="model" }
        @{ name="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"; type="model" }
        @{ name="lerobot-diffusion_pusht"; type="model" }

        @{ name="bookcorpus"; type="dataset" }
        @{ name="lerobot-pusht"; type="dataset" }
        @{ name="fashion-mnist"; type="dataset" }
        @{ name="hliang001-flickr2k"; type="dataset" }
        @{ name="rajpurkar-squad"; type="dataset" }

        @{ name="google-research-bert"; type="code" }
        @{ name="ptm-recommendation-with-transformers"; type="code" }
        @{ name="lerobot"; type="code" }
        @{ name="fashion-clip"; type="code" }
        @{ name="microsoft-git"; type="code" }
        @{ name="moondream"; type="code" }
        @{ name="mv-lab-swin2sr"; type="code" }
        @{ name="transformers-research-projects-distillation"; type="code" }
        @{ name="openai-whisper"; type="code" }
    ) | ForEach-Object { Normalize $_ }

    # Compare sets (order independent)
    $diff1 = Compare-Object -ReferenceObject $expectedSet -DifferenceObject $actualSet
    $diff2 = Compare-Object -ReferenceObject $actualSet -DifferenceObject $expectedSet

    if ($diff1.Count -gt 0 -or $diff2.Count -gt 0) {
        Write-Host "Expected vs Actual differences:" -ForegroundColor Red
        $diff1
        $diff2
        throw "Returned JSON does not match expected artifact list."
    }
}

# === POST /artifacts ({"name":"*","types":["code"]}) ===
Test-Call 'POST /artifacts name="*", types=["code"]' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":["code"]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    function Normalize {
        param($item)
        return ([PSCustomObject]@{
            name = $item.name
            type = $item.type
        } | ConvertTo-Json -Compress)
    }

    $actualSet = $json | ForEach-Object { Normalize $_ }

    $expectedSet = @(
        @{ name="google-research-bert"; type="code" }
        @{ name="ptm-recommendation-with-transformers"; type="code" }
        @{ name="lerobot"; type="code" }
        @{ name="fashion-clip"; type="code" }
        @{ name="microsoft-git"; type="code" }
        @{ name="moondream"; type="code" }
        @{ name="mv-lab-swin2sr"; type="code" }
        @{ name="transformers-research-projects-distillation"; type="code" }
        @{ name="openai-whisper"; type="code" }
    ) | ForEach-Object { Normalize $_ }

    # Compare expected ↔ actual (order-insensitive)
    $diff1 = Compare-Object -ReferenceObject $expectedSet -DifferenceObject $actualSet
    $diff2 = Compare-Object -ReferenceObject $actualSet -DifferenceObject $expectedSet

    if ($diff1.Count -gt 0 -or $diff2.Count -gt 0) {
        Write-Host "Expected vs Actual differences:" -ForegroundColor Red
        $diff1
        $diff2
        throw "Returned JSON does not match expected CODE artifact list."
    }
}

# === POST /artifacts ({"name":"*","types":["model"]}) ===
Test-Call 'POST /artifacts name="*", types=["model"] (again)' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":["model"]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    function Normalize {
        param($item)
        return ([PSCustomObject]@{
            name = $item.name
            type = $item.type
        } | ConvertTo-Json -Compress)
    }

    $actualSet = $json | ForEach-Object { Normalize $_ }

    $expectedSet = @(
        @{ name="distilbert-base-uncased-distilled-squad"; type="model" }
        @{ name="audience_classifier_model"; type="model" }
        @{ name="bert-base-uncased"; type="model" }
        @{ name="patrickjohncyh-fashion-clip"; type="model" }
        @{ name="WinKawaks-vit-tiny-patch16-224"; type="model" }
        @{ name="microsoft-git-base"; type="model" }
        @{ name="vikhyatk-moondream2"; type="model" }
        @{ name="caidas-swin2SR-lightweight-x2-64"; type="model" }
        @{ name="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"; type="model" }
        @{ name="lerobot-diffusion_pusht"; type="model" }
    ) | ForEach-Object { Normalize $_ }

    # Compare expected ↔ actual (order-insensitive)
    $diff1 = Compare-Object -ReferenceObject $expectedSet -DifferenceObject $actualSet
    $diff2 = Compare-Object -ReferenceObject $actualSet -DifferenceObject $expectedSet

    if ($diff1.Count -gt 0 -or $diff2.Count -gt 0) {
        Write-Host "Expected vs Actual differences:" -ForegroundColor Red
        $diff1
        $diff2
        throw "Returned JSON does NOT match expected MODEL artifact list."
    }
}


# === POST /artifacts ({"name":"*","types":["dataset"]}) ===
Test-Call 'POST /artifacts name="*", types=["dataset"]' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":["dataset"]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    function Normalize {
        param($item)
        return ([PSCustomObject]@{
            name = $item.name
            type = $item.type
        } | ConvertTo-Json -Compress)
    }

    $actualSet = $json | ForEach-Object { Normalize $_ }

    $expectedSet = @(
        @{ name="bookcorpus"; type="dataset" }
        @{ name="lerobot-pusht"; type="dataset" }
        @{ name="fashion-mnist"; type="dataset" }
        @{ name="hliang001-flickr2k"; type="dataset" }
        @{ name="rajpurkar-squad"; type="dataset" }
    ) | ForEach-Object { Normalize $_ }

    # Compare sets (order-insensitive)
    $diff1 = Compare-Object -ReferenceObject $expectedSet -DifferenceObject $actualSet
    $diff2 = Compare-Object -ReferenceObject $actualSet -DifferenceObject $expectedSet

    if ($diff1.Count -gt 0 -or $diff2.Count -gt 0) {
        Write-Host "Expected vs Actual differences:" -ForegroundColor Red
        $diff1
        $diff2
        throw "Returned JSON does NOT match expected DATASET list."
    }
}

# ------------------------------------
#  ARTIFACT SEARCH (NAME MATCH EXACT)
# ------------------------------------

Test-Call 'POST /artifacts name="vikhyatk-moondream2"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"vikhyatk-moondream2","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "vikhyatk-moondream2" -or $json.type -ne "model") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}


Test-Call 'POST /artifacts name="moondream"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"moondream","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "moondream" -or $json.type -ne "code") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}


Test-Call 'POST /artifacts name="caidas-swin2SR-lightweight-x2-64"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"caidas-swin2SR-lightweight-x2-64","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "caidas-swin2SR-lightweight-x2-64" -or $json.type -ne "model") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="hliang001-flickr2k"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"hliang001-flickr2k","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "hliang001-flickr2k" -or $json.type -ne "dataset") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="mv-lab-swin2sr"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"mv-lab-swin2sr","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "mv-lab-swin2sr" -or $json.type -ne "code") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="distilbert-base-uncased-distilled-squad"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"distilbert-base-uncased-distilled-squad","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "distilbert-base-uncased-distilled-squad" -or $json.type -ne "model") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="rajpurkar-squad"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"rajpurkar-squad","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "rajpurkar-squad" -or $json.type -ne "dataset") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="transformers-research-projects-distillation"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"transformers-research-projects-distillation","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "transformers-research-projects-distillation" -or $json.type -ne "code") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="openai-whisper"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"openai-whisper","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "openai-whisper" -or $json.type -ne "code") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="audience_classifier_model"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"audience_classifier_model","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "audience_classifier_model" -or $json.type -ne "model") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="bert-base-uncased"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"bert-base-uncased","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "bert-base-uncased" -or $json.type -ne "model") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="bookcorpus"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"bookcorpus","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "bookcorpus" -or $json.type -ne "dataset") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}

Test-Call 'POST /artifacts name="google-research-bert"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"google-research-bert","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    if ($json.name -ne "google-research-bert" -or $json.type -ne "code") {
        throw "Object did not match expected name/type. Got: $(ConvertTo-Json $json -Compress)"
    }
}


# -------------------------------
#  GET ALL ARTIFACT METADATA
# -------------------------------

Test-Call 'POST /artifacts name="*", types=[] (all metadata)' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"*","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)

    # Convert expected list (names & types only)
    $expected = @(
        @{ name="distilbert-base-uncased-distilled-squad"; type="model" }
        @{ name="audience_classifier_model"; type="model" }
        @{ name="bert-base-uncased"; type="model" }
        @{ name="patrickjohncyh-fashion-clip"; type="model" }
        @{ name="WinKawaks-vit-tiny-patch16-224"; type="model" }
        @{ name="microsoft-git-base"; type="model" }
        @{ name="vikhyatk-moondream2"; type="model" }
        @{ name="caidas-swin2SR-lightweight-x2-64"; type="model" }
        @{ name="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"; type="model" }
        @{ name="lerobot-diffusion_pusht"; type="model" }

        @{ name="bookcorpus"; type="dataset" }
        @{ name="lerobot-pusht"; type="dataset" }
        @{ name="fashion-mnist"; type="dataset" }
        @{ name="hliang001-flickr2k"; type="dataset" }
        @{ name="rajpurkar-squad"; type="dataset" }

        @{ name="google-research-bert"; type="code" }
        @{ name="ptm-recommendation-with-transformers"; type="code" }
        @{ name="lerobot"; type="code" }
        @{ name="fashion-clip"; type="code" }
        @{ name="microsoft-git"; type="code" }
        @{ name="moondream"; type="code" }
        @{ name="mv-lab-swin2sr"; type="code" }
        @{ name="transformers-research-projects-distillation"; type="code" }
        @{ name="openai-whisper"; type="code" }
    )

    # Reduce API result to comparable form (name + type only)
    $actual = $json | ForEach-Object {
        @{ name = $_.name; type = $_.type }
    }

    # 1️⃣ SAME LENGTH?
    if ($actual.Count -ne $expected.Count) {
        throw "Mismatch count: Expected $($expected.Count) items, got $($actual.Count)."
    }

    # 2️⃣ COMPARE SETS (order-independent)
    foreach ($exp in $expected) {
        $match = $actual | Where-Object { $_.name -eq $exp.name -and $_.type -eq $exp.type }
        if (-not $match) {
            throw "Missing expected item: $(ConvertTo-Json $exp -Compress)"
        }
    }

    # 3️⃣ CHECK FOR UNEXPECTED EXTRA ITEMS
    foreach ($act in $actual) {
        $match = $expected | Where-Object { $_.name -eq $act.name -and $_.type -eq $act.type }
        if (-not $match) {
            throw "Unexpected item in API response: $(ConvertTo-Json $act -Compress)"
        }
    }
}


# -------------------------------
#  RAW GET ARTIFACT REQUESTS
#  (now using real IDs from earlier POSTs)
# -------------------------------

Test-Call "GET /artifacts/model/{distilbertModelId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/model/$distilbertModelId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "distilbert-base-uncased-distilled-squad") {
        throw "Expected metadata.name='distilbert-base-uncased-distilled-squad' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "model") {
        throw "Expected metadata.type='model' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/distilbert-base-uncased-distilled-squad"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/dataset/{bookcorpusDatasetId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/dataset/$bookcorpusDatasetId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "bookcorpus") {
        throw "Expected metadata.name='bookcorpus' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "dataset") {
        throw "Expected metadata.type='dataset' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/code/{googleResearchBertCodeId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/code/$googleResearchBertCodeId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "google-research-bert") {
        throw "Expected metadata.name='google-research-bert' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "code") {
        throw "Expected metadata.type='code' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://github.com/google-research/bert"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/model/{patrickFashionClipModelId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/model/$patrickFashionClipModelId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "patrickjohncyh-fashion-clip") {
        throw "Expected metadata.name='patrickjohncyh-fashion-clip' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "model") {
        throw "Expected metadata.type='model' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/patrickjohncyh/fashion-clip"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/dataset/{rajpurkarSquadDatasetId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/dataset/$rajpurkarSquadDatasetId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "rajpurkar-squad") {
        throw "Expected metadata.name='rajpurkar-squad' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "dataset") {
        throw "Expected metadata.type='dataset' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/datasets/rajpurkar/squad"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/code/{ptmRecommendationCodeId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/code/$ptmRecommendationCodeId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "ptm-recommendation-with-transformers") {
        throw "Expected metadata.name='ptm-recommendation-with-transformers' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "code") {
        throw "Expected metadata.type='code' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://github.com/Parth1811/ptm-recommendation-with-transformers.git"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/code/{lerobotCodeId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/code/$lerobotCodeId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "lerobot") {
        throw "Expected metadata.name='lerobot' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "code") {
        throw "Expected metadata.type='code' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://github.com/huggingface/lerobot/tree/main"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/model/{audienceClassifierModelId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/model/$audienceClassifierModelId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "audience_classifier_model") {
        throw "Expected metadata.name='audience_classifier_model' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "model") {
        throw "Expected metadata.type='model' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/parvk11/audience_classifier_model"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/model/{bertBaseId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/model/$bertBaseId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "bert-base-uncased") {
        throw "Expected metadata.name='bert-base-uncased' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "model") {
        throw "Expected metadata.type='model' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/google-bert/bert-base-uncased"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/dataset/{lerobotPushtDatasetId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/dataset/$lerobotPushtDatasetId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "lerobot-pusht") {
        throw "Expected metadata.name='lerobot-pusht' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "dataset") {
        throw "Expected metadata.type='dataset' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://huggingface.co/datasets/lerobot/pusht"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

Test-Call "GET /artifacts/code/{fashionClipCodeId}" {
    Invoke-WebRequest -Uri "$BASE/artifacts/code/$fashionClipCodeId" -Method Get
} -ExpectedStatus @(200, 201) -Assert {
    param($json) 
    if ($json.metadata.name -ne "fashion-clip") {
        throw "Expected metadata.name='fashion-clip' but got '$($json.metadata.name)'"
    }

    if ($json.metadata.type -ne "code") {
        throw "Expected metadata.type='code' but got '$($json.metadata.type)'"
    }

    if (-not $json.metadata.PSObject.Properties.Match("id")) {
        throw "Expected metadata.id field to exist"
    } 
    $expectedUrl = "https://github.com/patrickjohncyh/fashion-clip"
    if ($json.data.url -ne $expectedUrl) {
        throw "Expected data.url='$expectedUrl' but got '$($json.data.url)'"
    }

    if (-not $json.data.PSObject.Properties.Match("download_url")) {
        throw "Expected data.download_url field to exist"
    }
}

# -------------------------------
#  NAME-BASED SEARCHES (last batch)
# -------------------------------

Test-Call 'POST /artifacts name="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "model") {
        throw "Expected type 'model' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}


Test-Call 'POST /artifacts name="ptm-recommendation-with-transformers"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"ptm-recommendation-with-transformers","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "ptm-recommendation-with-transformers"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "code") {
        throw "Expected type 'code' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="lerobot-diffusion_pusht"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"lerobot-diffusion_pusht","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "lerobot-diffusion_pusht"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "model") {
        throw "Expected type 'model' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="lerobot-pusht"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"lerobot-pusht","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "lerobot-pusht"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "dataset") {
        throw "Expected type 'dataset' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="lerobot"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"lerobot","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "lerobot"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "code") {
        throw "Expected type 'code' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="patrickjohncyh-fashion-clip"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"patrickjohncyh-fashion-clip","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "patrickjohncyh-fashion-clip"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "model") {
        throw "Expected type 'model' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="fashion-mnist"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"fashion-mnist","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "fashion-mnist"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "dataset") {
        throw "Expected type 'dataset' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="fashion-clip"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"fashion-clip","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "fashion-clip"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "code") {
        throw "Expected type 'code' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="WinKawaks-vit-tiny-patch16-224"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"WinKawaks-vit-tiny-patch16-224","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "WinKawaks-vit-tiny-patch16-224"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "model") {
        throw "Expected type 'model' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="microsoft-git-base"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"microsoft-git-base","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "microsoft-git-base"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "model") {
        throw "Expected type 'model' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifacts name="microsoft-git"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifacts" `
        -Method Post `
        -ContentType "application/json" `
        -Body '[{"name":"microsoft-git","types":[]}]'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "microsoft-git"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "code") {
        throw "Expected type 'code' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

# -------------------------------
#  REGEX SEARCHES (second batch)
# -------------------------------

Test-Call 'POST /artifact/byRegEx ".*bookcorpus.*"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":".*bookcorpus.*"}'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "bookcorpus"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "dataset") {
        throw "Expected type 'dataset' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

Test-Call 'POST /artifact/byRegEx "google-research-bert"' {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":"google-research-bert"}'
} -ExpectedStatus @(200, 201) -Assert {
    param($json)
    $expectedName = "google-research-bert"
    if ($json.name -ne $expectedName) {
        throw "Expected name '$expectedName' but got '$($json.name)'"
    }

    if ($json.type -ne "code") {
        throw "Expected type 'dataset' but got '$($json.type)'"
    }

    if (-not $json.PSObject.Properties.Match("id")) {
        throw "Expected 'id' field to exist, but it was missing"
    }
}

# -------------------------------
#  REGEX SEARCH TESTS (first batch)
# -------------------------------

Test-Call "POST /artifact/byRegEx (a|aa)*$" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":"(a|aa)*$"}'
} -ExpectedStatus @(400)

Test-Call "POST /artifact/byRegEx (a+)+$" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":"(a+)+$"}'
} -ExpectedStatus @(400)

Test-Call "POST /artifact/byRegEx (a{1,99999}){1,99999}$" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":"(a{1,99999}){1,99999}$"}'
} -ExpectedStatus @(400)

Test-Call "POST /artifact/byRegEx ece461rules" {
    Invoke-WebRequest `
        -Uri "$BASE/artifact/byRegEx" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"regex":"ece461rules"}'
} -ExpectedStatus @(404)

$allModelIds = @(
    $distilbertModelId,
    $audienceClassifierModelId,
    $bertBaseId,
    $patrickFashionClipModelId,
    $winKawaksVitModelId,
    $microsoftGitBaseModelId,
    $vikhyatMoondream2ModelId,
    $caidasSwin2ModelId,
    $longNameModelId,
    $lerobotDiffusionModelId
)

foreach ($id in $allModelIds) {
    Test-Call "GET /artifact/model/$id/rate" {
        Invoke-WebRequest -Uri "$BASE/artifact/model/$id/rate" -Method Get
    } -ExpectedStatus @(200, 404) -Assert {
        param($json)        
    }
}

Write-Host "`n🎉 ALL TESTS COMPLETE" -ForegroundColor Green
