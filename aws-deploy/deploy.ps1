<#
.SYNOPSIS
    One-click deployment script for the Log Analyzer serverless stack.
.PARAMETER LogGroups
    Optional JSON array of CloudWatch log group names to subscribe to the processor.
    Example: -LogGroups '["/aws/lambda/my-fn","/ecs/my-service"]'
#>
param(
    [string]$LogGroups = ""
)

$ErrorActionPreference = "Stop"

$env:AWS_PROFILE = "419466290453_AdministratorAccess"
$env:AWS_PAGER = ""

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Log Analyzer — CDK Deploy" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# --- Step 1: Python virtual environment ---
Write-Host "[1/5] Setting up Python virtual environment..." -ForegroundColor Yellow

if (Test-Path ".venv") {
    if (-not (Test-Path ".venv\Scripts\pip.exe")) {
        Write-Host "  Broken venv detected — removing and recreating..." -ForegroundColor DarkYellow
        Remove-Item -Recurse -Force ".venv"
    }
}
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}
& .venv\Scripts\activate.ps1

# --- Step 2: Install CDK Python dependencies ---
Write-Host "[2/5] Installing CDK dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# --- Step 3: Build Lambda Layer ---
Write-Host "[3/5] Building Lambda Layer..." -ForegroundColor Yellow

$layerTarget = "lambda_layer\python"
if (Test-Path "lambda_layer") {
    Remove-Item -Recurse -Force "lambda_layer"
}
New-Item -ItemType Directory -Path $layerTarget -Force | Out-Null

$lambdaReqs = "lambda_code\requirements.txt"
$lockFile = "lambda_code\requirements.lock"

Write-Host "  Resolving dependencies for manylinux2014_x86_64 / Python 3.12..."
uv pip compile $lambdaReqs `
    --python-platform manylinux2014_x86_64 `
    --python-version 3.12 `
    -o $lockFile

Write-Host "  Installing binary wheels into layer directory..."
pip install `
    -r $lockFile `
    --target $layerTarget `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary :all: `
    --no-deps

# --- Step 4: CDK Bootstrap ---
Write-Host "[4/5] Running CDK bootstrap (idempotent)..." -ForegroundColor Yellow
npx cdk bootstrap

# --- Step 5: CDK Deploy ---
Write-Host "[5/5] Deploying stack..." -ForegroundColor Yellow

$cdkArgs = @("cdk", "deploy", "--require-approval", "never", "--outputs-file", "cdk-outputs.json")
if ($LogGroups) {
    $cdkArgs += @("-c", "log_group_names=$LogGroups")
}
npx @cdkArgs

# --- Print outputs ---
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

if (Test-Path "cdk-outputs.json") {
    $outputs = Get-Content "cdk-outputs.json" | ConvertFrom-Json
    $stackOutputs = $outputs.LogAnalyzerStack
    if ($stackOutputs) {
        Write-Host "  API Gateway URL : $($stackOutputs.ApiGatewayUrl)" -ForegroundColor White
        Write-Host "  Dashboard URL   : $($stackOutputs.DashboardSiteUrl)" -ForegroundColor White
        Write-Host "  Processor Lambda: $($stackOutputs.ProcessorFnName)" -ForegroundColor White
        Write-Host "  API Lambda      : $($stackOutputs.ApiFnName)" -ForegroundColor White
        Write-Host "  Test Generator  : $($stackOutputs.TestGenFnName)" -ForegroundColor White
    }
}

Write-Host ""
