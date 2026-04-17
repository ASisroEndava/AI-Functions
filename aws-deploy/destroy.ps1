<#
.SYNOPSIS
    Tears down the Log Analyzer serverless stack and cleans up local artifacts.
#>

$ErrorActionPreference = "Stop"

$env:AWS_PROFILE = "419466290453_AdministratorAccess"
$env:AWS_PAGER = ""
$env:JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION = "1"

Write-Host "`n========================================" -ForegroundColor Red
Write-Host "  Log Analyzer — CDK Destroy" -ForegroundColor Red
Write-Host "========================================`n" -ForegroundColor Red

# Activate venv if present
if (Test-Path ".venv\Scripts\activate.ps1") {
    & .venv\Scripts\activate.ps1
}

# Destroy the stack
Write-Host "Destroying CDK stack..." -ForegroundColor Yellow
npx cdk destroy --force

# Clean up local build artifacts
Write-Host "Cleaning up local artifacts..." -ForegroundColor Yellow
$artifacts = @("cdk-outputs.json", "lambda_layer", "cdk.out")
foreach ($item in $artifacts) {
    if (Test-Path $item) {
        Remove-Item -Recurse -Force $item
        Write-Host "  Removed: $item" -ForegroundColor DarkGray
    }
}

Write-Host "`nStack destroyed and artifacts cleaned up." -ForegroundColor Green
Write-Host ""
