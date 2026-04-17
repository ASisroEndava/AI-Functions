# Log Analyzer — AWS Serverless Deployment Guide

Manual step-by-step instructions to deploy the Log Analyzer stack to AWS from a Windows machine.

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| **Python** | 3.12+ | Lambda runtime, CDK app |
| **Node.js** | 18+ | AWS CDK CLI (`npx cdk`) |
| **AWS CLI** | 2.x | Credentials & region configuration |
| **uv** | 0.2+ | Cross-platform dependency resolution for Lambda Layer |
| **pip** | 23+ | Package installation (comes with Python) |
| **Git** | any | (optional) version control |

---

## 1. Install Prerequisites (if not already configured)

Run these in an **elevated PowerShell** terminal.

### 1.1 Python 3.12+

```powershell
# Option A: winget (Windows 10/11)
winget install Python.Python.3.12

# Option B: download from https://www.python.org/downloads/
# During install, check "Add python.exe to PATH"

# Verify
py --version
```

### 1.2 Node.js 18+

```powershell
# Option A: winget
winget install OpenJS.NodeJS.LTS

# Option B: download from https://nodejs.org/

# Verify
node --version
npm --version
```

### 1.3 AWS CLI v2

```powershell
# Option A: winget
winget install Amazon.AWSCLI

# Option B: MSI installer from https://aws.amazon.com/cli/

# Verify
aws --version
```

### 1.4 uv (Astral package manager)

```powershell
# Option A: pip
pip install uv

# Option B: standalone installer
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

---

## 2. Configure AWS Credentials

The deployment needs credentials with permissions for CloudFormation, DynamoDB, Lambda, API Gateway, S3, IAM, and Bedrock.

### Option A: IAM User (Access Keys)

```powershell
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (e.g. us-east-1), Output format (json)
```

### Option B: AWS SSO

```powershell
aws configure sso
# Follow the prompts to set up SSO profile

# Set the profile for this session
$env:AWS_PROFILE = "your-sso-profile-name"

# Login
aws sso login --profile $env:AWS_PROFILE
```

### Option C: Environment Variables

```powershell
$env:AWS_ACCESS_KEY_ID = "AKIA..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_DEFAULT_REGION = "us-east-1"
```

### Verify credentials work

```powershell
aws sts get-caller-identity
```

---

## 3. Enable Amazon Bedrock Model Access

The stack uses **Claude 3.5 Haiku** via Amazon Bedrock. You must enable model access before deploying.

1. Open the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** (left sidebar)
3. Click **Manage model access**
4. Enable **Anthropic → Claude 3.5 Haiku**
5. Click **Save changes** and wait for status to become **Access granted**

> **Important:** The model ID uses a cross-region inference profile (`us.anthropic.claude-3-5-haiku-20241022-v1:0`). Ensure the model is enabled in the region you're deploying to.

---

## 4. Deploy the Stack

### 4.1 Navigate to the `aws-deploy` directory

```powershell
cd "c:\Code Tests\Test\AI-Functions Generate from spec\aws-deploy"
```

### 4.2 Quick Deploy (using the provided script)

```powershell
.\deploy.ps1
```

To subscribe external CloudWatch log groups to the processor:

```powershell
.\deploy.ps1 -LogGroups '["/aws/lambda/my-fn", "/ecs/my-service"]'
```

### 4.3 Manual Deploy (step by step)

If you prefer to run each step individually:

#### Step 1 — Create Python virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\activate.ps1
```

#### Step 2 — Install CDK Python dependencies

```powershell
pip install -r requirements.txt
```

#### Step 3 — Build the Lambda Layer

The Lambda Layer must contain Linux-compatible wheels (not Windows). This two-step process resolves and installs the correct packages:

```powershell
# Clean previous build
if (Test-Path "lambda_layer") { Remove-Item -Recurse -Force "lambda_layer" }
New-Item -ItemType Directory -Path "lambda_layer\python" -Force | Out-Null

# Resolve dependencies for Lambda's Linux runtime
uv pip compile lambda_code\requirements.txt `
    --python-platform manylinux2014_x86_64 `
    --python-version 3.12 `
    -o lambda_code\requirements.lock

# Install binary wheels into the layer directory
pip install `
    -r lambda_code\requirements.lock `
    --target lambda_layer\python `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary :all: `
    --no-deps
```

#### Step 4 — Bootstrap CDK (once per account/region)

```powershell
npx cdk bootstrap
```

#### Step 5 — Deploy

```powershell
npx cdk deploy --require-approval never --outputs-file cdk-outputs.json
```

With external log groups:

```powershell
npx cdk deploy --require-approval never --outputs-file cdk-outputs.json `
    -c log_group_names='["/aws/lambda/my-fn"]'
```

#### Step 6 — Retrieve outputs

```powershell
Get-Content cdk-outputs.json | ConvertFrom-Json | Select-Object -ExpandProperty LogAnalyzerStack
```

You'll see:
- **ApiGatewayUrl** — REST API base URL
- **DashboardSiteUrl** — S3 dashboard URL
- **ProcessorFnName** — CloudWatch processor Lambda
- **ApiFnName** — API handler Lambda
- **TestGenFnName** — Test log generator Lambda

---

## 5. Verify the Deployment

### 5.1 Open the dashboard

Copy the **DashboardSiteUrl** from the outputs and open it in a browser. Paste the **ApiGatewayUrl** into the API URL field and click **Save**.

### 5.2 Generate test logs

```powershell
aws lambda invoke `
    --function-name log-analyzer-test-generator `
    --payload '{"count": 5}' `
    --cli-binary-format raw-in-base64-out `
    response.json

Get-Content response.json
```

Wait ~30 seconds for CloudWatch to route the logs through the subscription filter to the processor Lambda, then **Refresh** the dashboard.

### 5.3 Analyze logs via API

```powershell
$apiUrl = "https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"

# Analyze raw logs
Invoke-RestMethod -Method POST -Uri "$apiUrl/api/analyze" `
    -ContentType "application/json" `
    -Body '{"logs": ["ERROR Connection refused to database primary-01", "INFO User login successful"]}'

# Get stats
Invoke-RestMethod -Uri "$apiUrl/api/stats"

# Get analyzed logs
Invoke-RestMethod -Uri "$apiUrl/api/logs"

# Correlate incidents
Invoke-RestMethod -Method POST -Uri "$apiUrl/api/correlate"

# View incidents
Invoke-RestMethod -Uri "$apiUrl/api/incidents"
```

---

## 6. Tear Down the Stack

### Quick destroy

```powershell
.\destroy.ps1
```

### Manual destroy

```powershell
.\.venv\Scripts\activate.ps1
npx cdk destroy --force

# Clean up local artifacts
Remove-Item -Recurse -Force cdk-outputs.json, lambda_layer, cdk.out -ErrorAction SilentlyContinue
```

---

## 7. Troubleshooting

### `uv` not found

```powershell
pip install uv
# or
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### `npx cdk` not found / Node.js errors

```powershell
# Ensure Node.js is on PATH
node --version

# If npx is slow on first run, it's downloading the CDK CLI — this is normal
# You can install it globally to speed up future runs:
npm install -g aws-cdk
```

### CDK Bootstrap fails — "Access Denied"

Your AWS credentials lack CloudFormation/S3 permissions. Ensure the IAM user/role has `AdministratorAccess` or at least:
- `cloudformation:*`
- `s3:*`
- `iam:*`
- `lambda:*`
- `apigateway:*`
- `dynamodb:*`
- `logs:*`
- `bedrock:InvokeModel`

### Lambda Layer build fails — "No matching distribution"

This means `pip` couldn't find a manylinux wheel for one of the dependencies. Ensure:
- `uv` is up to date: `pip install -U uv`
- You're using Python 3.12: `py --version`
- Your internet connection can reach PyPI

### Bedrock `ValidationException` or `AccessDeniedException`

- **ValidationException**: The model ID might be wrong. Verify the model is available in your region.
- **AccessDeniedException**: You haven't enabled model access in the Bedrock console (see Section 3).

### PowerShell execution policy error

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment activation fails

```powershell
# Remove and recreate
Remove-Item -Recurse -Force .venv
py -m venv .venv
.\.venv\Scripts\activate.ps1
```

---

## Architecture Overview

```
CloudWatch Logs ──► Subscription Filter ──► Processor Lambda ──► DynamoDB
                                                │
Browser ──► S3 Dashboard ──► API Gateway ──► API Lambda ──► DynamoDB
                                                │
                                           Amazon Bedrock
                                        (Claude 3.5 Haiku)
```

| Resource | Name |
|----------|------|
| DynamoDB (logs) | `log-analyzer-logs` |
| DynamoDB (incidents) | `log-analyzer-incidents` |
| Processor Lambda | `log-analyzer-cw-processor` |
| API Lambda | `log-analyzer-api` |
| Test Generator Lambda | `log-analyzer-test-generator` |
| API Gateway | `LogAnalyzerGateway` |
| S3 Bucket | auto-generated name |
