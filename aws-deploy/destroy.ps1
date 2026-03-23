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

if (-not $env:AWS_PROFILE) {
    $env:AWS_PROFILE = "AdministratorAccess-419466290453"
}

Write-Host "`n=== Log Analyzer AWS Destroy ===" -ForegroundColor Red

$destroyed = $false

if (Test-Path ".venv") {
    $VenvScripts = Join-Path (Join-Path $ScriptDir ".venv") "Scripts"
    $env:PATH = "$VenvScripts;$env:PATH"
    $env:VIRTUAL_ENV = Join-Path $ScriptDir ".venv"

    Write-Host "Destroying LogAnalyzerStack via CDK..." -ForegroundColor Yellow
    npx cdk destroy --force

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nStack destroyed successfully." -ForegroundColor Green
        $destroyed = $true
    } else {
        Write-Host "CDK destroy failed — falling back to AWS CLI..." -ForegroundColor Yellow
    }
}

if (-not $destroyed) {
    Write-Host "Destroying LogAnalyzerStack via AWS CLI..." -ForegroundColor Yellow
    aws cloudformation delete-stack --stack-name LogAnalyzerStack
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFailed to delete stack — check CloudFormation console." -ForegroundColor Red
        exit 1
    }
    Write-Host "Waiting for stack deletion to complete..." -ForegroundColor Gray
    aws cloudformation wait stack-delete-complete --stack-name LogAnalyzerStack
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nStack destroyed successfully." -ForegroundColor Green
    } else {
        Write-Host "`nStack deletion timed out or failed — check CloudFormation console." -ForegroundColor Red
    }
}

# Clean up local artifacts
if (Test-Path "cdk-outputs.json") { Remove-Item "cdk-outputs.json" }
if (Test-Path "lambda_layer") { Remove-Item -Recurse -Force "lambda_layer" }
if (Test-Path "cdk.out") { Remove-Item -Recurse -Force "cdk.out" }

Write-Host "Local build artifacts cleaned up.`n" -ForegroundColor Gray
