# Log Analyzer — Architecture Document

## 1. System Context

The Log Analyzer is a dual-mode application:

- **Local mode**: CLI + FastAPI server running on a developer machine, persisting to SQLite.
- **Serverless mode**: Fully managed AWS infrastructure processing CloudWatch logs in real time.

Both modes share the same AI analysis pipeline built on `strands-ai-functions` with Amazon Bedrock.

---

## 2. High-Level Architecture

### 2.1 Local Mode

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────┐
│  Log File   │────►│  log_reader   │────►│   analyzer.py  │────►│ storage  │
│ (*.txt)     │     │  (parser)     │     │  (AI pipeline) │     │ (SQLite) │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────┘
                                                                      │
┌─────────────┐     ┌──────────────┐                                  │
│  Browser    │◄───►│   api.py     │◄─────────────────────────────────┘
│ (dashboard) │     │  (FastAPI)   │
└─────────────┘     └──────────────┘
```

**Components:**

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| `cli.py` | Python script | Reads log file, runs pipeline, outputs to terminal + files |
| `log_reader.py` | Python (regex) | Parses raw log files, extracts timestamp/source/message |
| `analyzer.py` | strands-ai-functions | AI pipeline: classify → categorize → summarize → suggest → validate |
| `storage.py` | SQLite3 | CRUD operations for logs and incidents |
| `api.py` | FastAPI + Uvicorn | REST API serving the dashboard and data endpoints |
| `dashboard.html` | Vanilla HTML/CSS/JS | Single-page dark-themed dashboard |

### 2.2 Serverless Mode (AWS)

```
┌────────────────────┐
│  CloudWatch Logs   │
│  (any log group)   │
└────────┬───────────┘
         │ Subscription Filter
         ▼
┌────────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Processor Lambda  │────►│  analyzer.py     │────►│  DynamoDB     │
│  (cloudwatch_      │     │  (AI pipeline    │     │  (logs +      │
│   handler.py)      │     │   + Bedrock)     │     │   incidents)  │
└────────────────────┘     └──────────────────┘     └───────┬───────┘
                                                            │
┌────────────────────┐     ┌──────────────────┐             │
│  S3 Static Site    │     │  API Lambda      │◄────────────┘
│  (dashboard HTML)  │◄───►│  (api_handler.py)│
└────────────────────┘     └──────┬───────────┘
                                  │
                           ┌──────┴───────────┐
                           │  API Gateway     │
                           │  (REST)          │
                           └──────────────────┘

┌────────────────────┐
│  Test Generator    │──► writes to its own CloudWatch log group
│  Lambda            │    (subscribed to Processor Lambda)
└────────────────────┘
```

**AWS Resources:**

| Resource | Service | Purpose |
|----------|---------|---------|
| `log-analyzer-logs` | DynamoDB | Stores analyzed log entries with GSIs for level and category |
| `log-analyzer-incidents` | DynamoDB | Stores incident correlation reports |
| `log-analyzer-cw-processor` | Lambda (Python 3.12) | Receives CloudWatch events, runs AI pipeline, writes to DynamoDB |
| `log-analyzer-api` | Lambda (Python 3.12) | REST API handler for dashboard queries |
| `log-analyzer-test-generator` | Lambda (Python 3.12) | Generates sample logs for testing |
| `LogAnalyzerGateway` | API Gateway (REST) | Exposes API Lambda as HTTP endpoints |
| `DashboardSiteBucket` | S3 (static website) | Hosts the dashboard HTML |
| `AiFuncsDepsLayer` | Lambda Layer | Shared dependencies: strands-ai-functions, pydantic |
| Subscription Filters | CloudWatch Logs | Routes log events to the processor Lambda |

---

## 3. AI Pipeline Architecture

The core analysis pipeline chains 5 AI function calls sequentially per log entry:

```
                    ┌─────────────────────┐
                    │     Raw log entry    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
              Step 1│  classify_severity  │  → LogLevel
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
              Step 2│   categorize_log    │  → category string
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
              Step 3│   summarize_log     │  → summary (≤30 words)
                    │  [post-condition:   │    max 3 attempts
                    │   word count ≤ 30]  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
              Step 4│    suggest_fix      │  → suggestion string
                    │ (WARNING+ only)     │    (skipped for DEBUG/INFO)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
              Step 5│validate_suggestion  │  → PostConditionResult
                    │  quality            │    (AI post-condition,
                    │  [retry up to 2x]   │     re-generates if fails)
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    LogAnalysis       │
                    │    (final result)    │
                    └─────────────────────┘
```

**Correlation pipeline** (separate, on-demand):

```
┌─────────────────────────┐
│ All WARNING/ERROR/CRIT  │
│ logs from storage       │
└────────────┬────────────┘
             │
  ┌──────────▼──────────┐
  │   correlate_logs    │  → IncidentReport
  │  [post-condition:   │    max 3 attempts
  │   ≥1 action]        │
  └─────────────────────┘
```

---

## 4. Data Flow

### 4.1 Local Mode — CLI Flow

1. User runs `uv run cli.py [logfile]`
2. `log_reader.parse_log_file()` reads and parses the file
3. For each entry, `analyzer.analyze_log()` runs the AI pipeline via Bedrock
4. Results are saved to `analysis_results.json` and `logs.db` (SQLite)
5. Problem logs are correlated into an incident report
6. Terminal displays color-coded results

### 4.2 Local Mode — API Flow

1. User starts `uvicorn api:app --port 8080`
2. Browser loads `dashboard.html` from `/` endpoint
3. Dashboard fetches stats and logs from `/api/stats`, `/api/logs`
4. User can upload files, analyze raw logs, correlate incidents via API
5. All data persisted in `logs.db`

### 4.3 Serverless Mode — Automatic Processing

1. An application writes logs to a subscribed CloudWatch Log Group
2. CloudWatch Subscription Filter triggers the Processor Lambda
3. Lambda decodes the base64+gzipped event, extracts log messages
4. Runtime noise (START/END/REPORT) is filtered out
5. Each valid message passes through the AI pipeline (Bedrock via strands)
6. Results are written to DynamoDB `log-analyzer-logs`
7. Dashboard (S3) calls API Gateway → API Lambda → DynamoDB to display results

### 4.4 Serverless Mode — On-Demand Analysis

1. User sends `POST /api/analyze {"logs": [...]}` to API Gateway
2. API Lambda runs the AI pipeline for each log
3. Results stored in DynamoDB and returned in the response

---

## 5. Infrastructure as Code

### CDK Stack Structure (`stack.py`)

```
LogAnalyzerStack
├── _provision_tables()         → 2 DynamoDB tables + GSIs
├── _build_layer()              → Lambda Layer (strands-ai-functions + pydantic)
├── _bedrock_policy()           → IAM policy for Bedrock invoke
├── _processor_lambda()         → CloudWatch processor function
├── _api_lambda()               → REST API function
├── _rest_api()                 → API Gateway with 5 endpoint resources
├── _dashboard()                → S3 bucket + BucketDeployment
├── _cw_subscriptions()         → Optional external log group subscriptions
└── _test_generator_lambda()    → Test log generator + subscription to processor
```

### Deployment Pipeline (`deploy.ps1`)

```
Step 1: Create Python venv + install CDK deps (aws-cdk-lib, constructs)
Step 2: Build Lambda Layer
        └── uv pip compile (resolve for manylinux2014_x86_64 / Python 3.12)
        └── pip install --target lambda_layer/python --only-binary :all:
Step 3: CDK bootstrap (first-time per account/region)
Step 4: CDK deploy (synthesize + CloudFormation changeset)
Step 5: Print output URLs
```

---

## 6. Network and Security Architecture

```
┌─ Internet ───────────────────────────────────────────────┐
│                                                          │
│  Browser ──► S3 Website (dashboard HTML)                 │
│  Browser ──► API Gateway ──► API Lambda ──► DynamoDB     │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌─ AWS Internal ───────────────────────────────────────────┐
│                                                          │
│  CloudWatch Logs ──► Subscription Filter ──► Processor   │
│  Processor Lambda ──► Bedrock (AI model invoke)          │
│  Processor Lambda ──► DynamoDB (write results)           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**IAM Permissions:**

| Lambda | Permissions |
|--------|-------------|
| Processor | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, DynamoDB read/write on both tables |
| API | Same as Processor |
| Test Generator | CloudWatch Logs write (automatic via Lambda execution role) |

**CORS:** API Gateway configured with `allow_origins=*`, `allow_methods=*`.

---

## 7. Technology Stack Summary

| Layer | Local Mode | Serverless Mode |
|-------|-----------|-----------------|
| **Language** | Python 3.12+ | Python 3.12 (Lambda runtime) |
| **AI Framework** | strands-ai-functions | strands-ai-functions (Lambda Layer) |
| **AI Provider** | Amazon Bedrock (default model) | Amazon Bedrock (Claude 3.5 Haiku, cross-region profile) |
| **Web Framework** | FastAPI + Uvicorn | API Gateway + Lambda handler |
| **Storage** | SQLite (`logs.db`) | DynamoDB (2 tables, on-demand) |
| **Frontend** | Inline HTML served by FastAPI | Static HTML on S3 |
| **IaC** | N/A | AWS CDK (Python) |
| **Package Manager** | uv | uv (compile) + pip (layer install) |
| **Deployment** | `uv run` | `deploy.ps1` (PowerShell) |
