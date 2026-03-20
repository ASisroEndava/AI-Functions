<#
.SYNOPSIS
    Tear down all Log Analyzer AWS infrastructure.
.DESCRIPTION
    Runs cdk destroy to remove the entire CloudFormation stack,
    including DynamoDB tables, Lambda functions, API Gateway, and S3 bucket.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "`n=== Log Analyzer AWS Destroy ===" -ForegroundColor Red

if (-not (Test-Path ".venv")) {
    Write-Host "No .venv found — was the stack ever deployed from here?" -ForegroundColor Yellow
    exit 1
}

Write-Host "Destroying LogAnalyzerStack..." -ForegroundColor Yellow
npx cdk destroy --force

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nStack destroyed successfully." -ForegroundColor Green
} else {
    Write-Host "`nDestroy may have failed — check CloudFormation console." -ForegroundColor Red
}

# Clean up local artifacts
if (Test-Path "cdk-outputs.json") { Remove-Item "cdk-outputs.json" }
if (Test-Path "lambda_layer") { Remove-Item -Recurse -Force "lambda_layer" }
if (Test-Path "cdk.out") { Remove-Item -Recurse -Force "cdk.out" }

Write-Host "Local build artifacts cleaned up.`n" -ForegroundColor Gray
