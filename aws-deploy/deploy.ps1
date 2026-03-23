<#
.SYNOPSIS
    One-click deploy of the Log Analyzer infrastructure to AWS.
.DESCRIPTION
    1. Creates a Python venv and installs CDK dependencies
    2. Builds Lambda Layer (pip install for Linux/x86_64)
    3. Bootstraps CDK (first-time only)
    4. Deploys the full stack
    5. Prints the API Gateway URL and Dashboard URL
.PARAMETER LogGroups
    Optional JSON array of CloudWatch Log Group names to subscribe.
    Example: -LogGroups '["/aws/lambda/my-fn","/ecs/my-svc"]'
#>
param(
    [string]$LogGroups = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not $env:AWS_PROFILE) {
    $env:AWS_PROFILE = "AdministratorAccess-419466290453"
}

$PipExe = Join-Path (Join-Path (Join-Path $ScriptDir ".venv") "Scripts") "pip.exe"
$PythonExe = Join-Path (Join-Path (Join-Path $ScriptDir ".venv") "Scripts") "python.exe"
$LayerDir = Join-Path (Join-Path $ScriptDir "lambda_layer") "python"
$LayerReqs = Join-Path (Join-Path $ScriptDir "lambda_code") "requirements.txt"

Write-Host "`n=== Log Analyzer AWS Deploy ===" -ForegroundColor Cyan

# ── Step 1: Python venv for CDK ─────────────────────────────────────
Write-Host "`n[1/5] Setting up CDK virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path $PipExe)) {
    if (Test-Path (Join-Path $ScriptDir ".venv")) {
        Write-Host "   Removing broken .venv (no pip)..." -ForegroundColor Gray
        Remove-Item -Recurse -Force (Join-Path $ScriptDir ".venv")
    }
    Write-Host "   Creating .venv..." -ForegroundColor Gray
    py -m venv .venv
    if (-not (Test-Path $PipExe)) {
        Write-Host "   ERROR: venv created but pip.exe not found. Ensure Python includes pip." -ForegroundColor Red
        exit 1
    }
}
Write-Host "   Installing CDK Python packages..." -ForegroundColor Gray
& $PipExe install -q -r requirements.txt
Write-Host "   Done." -ForegroundColor Green

# ── Step 2: Build Lambda Layer ───────────────────────────────────────
Write-Host "`n[2/5] Building Lambda Layer (Linux x86_64 packages)..." -ForegroundColor Yellow
$layerRoot = Join-Path $ScriptDir "lambda_layer"
if (Test-Path $layerRoot) {
    Remove-Item -Recurse -Force $layerRoot
}
New-Item -ItemType Directory -Path $LayerDir -Force | Out-Null

Write-Host "   Resolving dependencies with uv..." -ForegroundColor Gray
$LockFile = Join-Path (Join-Path $ScriptDir "lambda_code") "requirements.lock"
uv pip compile $LayerReqs --python-platform manylinux2014_x86_64 --python-version 3.12 -o $LockFile --quiet
Write-Host "   Installing locked packages for Linux/x86_64..." -ForegroundColor Gray
& $PipExe install `
    -r $LockFile `
    --target $LayerDir `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary=:all: `
    --no-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: pip install failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
Write-Host "   Layer built at: $LayerDir" -ForegroundColor Green

# ── Activate venv for CDK ─────────────────────────────────────────────
$VenvScripts = Join-Path (Join-Path $ScriptDir ".venv") "Scripts"
$env:PATH = "$VenvScripts;$env:PATH"
$env:VIRTUAL_ENV = Join-Path $ScriptDir ".venv"

# ── Step 3: CDK Bootstrap ────────────────────────────────────────────
Write-Host "`n[3/5] Bootstrapping CDK (if needed)..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
npx cdk bootstrap
$ErrorActionPreference = "Stop"
Write-Host "   Bootstrap step complete." -ForegroundColor Green

# ── Step 4: CDK Deploy ───────────────────────────────────────────────
Write-Host "`n[4/5] Deploying stack..." -ForegroundColor Yellow
$cdkArgs = @("cdk", "deploy", "--require-approval", "never", "--outputs-file", "cdk-outputs.json")
if ($LogGroups) {
    $cdkArgs += @("-c", "log_group_names=$LogGroups")
}
npx @cdkArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nDeploy FAILED. Check the errors above." -ForegroundColor Red
    exit 1
}

# ── Step 5: Print outputs ────────────────────────────────────────────
Write-Host "`n[5/5] Deployment complete!" -ForegroundColor Green
if (Test-Path "cdk-outputs.json") {
    $outputs = Get-Content "cdk-outputs.json" | ConvertFrom-Json
    $stack = $outputs."LogAnalyzerStack"
    Write-Host "`n  API Gateway URL     : $($stack.ApiGatewayUrl)" -ForegroundColor Cyan
    Write-Host "  Dashboard URL       : $($stack.DashboardSiteUrl)" -ForegroundColor Cyan
    Write-Host "  Processor Lambda    : $($stack.ProcessorLambdaName)" -ForegroundColor Gray
    Write-Host "  API Lambda          : $($stack.ApiLambdaName)" -ForegroundColor Gray
    Write-Host "  Test Generator      : $($stack.TestGeneratorLambdaName)" -ForegroundColor Gray
    Write-Host "`n  Paste the API Gateway URL into the dashboard's API field." -ForegroundColor Yellow
    Write-Host "  Generate test logs:  aws lambda invoke --function-name $($stack.TestGeneratorLambdaName) --payload '{""count"":10}' out.json`n" -ForegroundColor Yellow
}
