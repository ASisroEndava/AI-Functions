# Log Analyzer — Specification Document

## 1. Overview

**Product Name:** Log Analyzer con AI Functions

**Purpose:** An AI-powered log analysis system that ingests application logs, classifies them by severity and category using a pipeline of chained AI functions, generates human-readable summaries, suggests actionable fixes, and correlates related problem logs into incident reports.

**Target Users:** DevOps engineers, SREs, and developers who need automated triage of application logs.

---

## 2. Functional Requirements

### FR-01: Log Ingestion

| ID | Requirement |
|----|-------------|
| FR-01.1 | The system SHALL parse log files in common formats: `YYYY-MM-DD HH:MM:SS [source] message` and `YYYY-MM-DDTHH:MM:SSZ LEVEL message`. |
| FR-01.2 | The system SHALL accept plain-text log lines without timestamps or source tags. |
| FR-01.3 | The system SHALL extract timestamp, source (bracketed tag), and raw message from each line. |
| FR-01.4 | The system SHALL skip empty lines during parsing. |
| FR-01.5 | The system SHALL support ingestion via CLI (file path argument), REST API (JSON body or file upload), and CloudWatch Logs subscription (serverless mode). |

### FR-02: AI Analysis Pipeline

| ID | Requirement |
|----|-------------|
| FR-02.1 | Each log entry SHALL pass through a sequential pipeline of AI functions: classify severity → categorize → summarize → suggest fix → validate suggestion. |
| FR-02.2 | **Severity classification** SHALL return exactly one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| FR-02.3 | **Categorization** SHALL assign exactly one category from the set: `authentication`, `networking`, `database`, `filesystem`, `performance`, `security`, `configuration`, `application`, `deployment`. |
| FR-02.4 | **Summarization** SHALL produce a single sentence of at most 30 words. A post-condition SHALL enforce this constraint with up to 3 retry attempts. |
| FR-02.5 | **Fix suggestion** SHALL only be generated for logs classified as `WARNING`, `ERROR`, or `CRITICAL`. For `DEBUG`/`INFO` logs, suggestion SHALL be `"N/A"`. |
| FR-02.6 | **Suggestion validation** SHALL use an AI post-condition that evaluates whether the suggestion is actionable and specific. If validation fails, the suggestion SHALL be regenerated up to 2 times. If all attempts fail, confidence SHALL be downgraded to `"low"`. |
| FR-02.7 | Each pipeline step SHALL use the `@ai_function` decorator from the `ai_functions` library. |

### FR-03: Incident Correlation

| ID | Requirement |
|----|-------------|
| FR-03.1 | The system SHALL correlate all `WARNING`/`ERROR`/`CRITICAL` logs into an incident report. |
| FR-03.2 | An incident report SHALL contain: title, root cause, affected services, overall severity (`low`/`medium`/`high`/`critical`), recommended actions, and related log line numbers. |
| FR-03.3 | A post-condition SHALL enforce that every incident report contains at least one recommended action, with up to 3 retry attempts. |

### FR-04: Data Persistence

| ID | Requirement |
|----|-------------|
| FR-04.1 | **Local mode:** The system SHALL store analyzed logs and incidents in a SQLite database (`logs.db`). |
| FR-04.2 | **Local mode:** The system SHALL also export results to `analysis_results.json`. |
| FR-04.3 | **Serverless mode:** The system SHALL store analyzed logs in a DynamoDB table (`log-analyzer-logs`) with fields: `id` (UUID), `line`, `timestamp`, `source`, `raw`, `log_level`, `summary`, `suggestion`, `category`, `confidence`, `created_at`. |
| FR-04.4 | **Serverless mode:** The system SHALL store incidents in a separate DynamoDB table (`log-analyzer-incidents`) with fields: `id` (UUID), `title`, `root_cause`, `affected_services` (JSON), `severity`, `recommended_actions` (JSON), `related_log_lines` (JSON), `created_at`. |
| FR-04.5 | The logs table SHALL support querying by `log_level` and by `category` via global secondary indexes (GSIs). |

### FR-05: REST API

| ID | Requirement |
|----|-------------|
| FR-05.1 | `GET /api/logs` — List analyzed logs with optional filters: `level`, `source`, `category`, `search`, `limit`, `offset`. |
| FR-05.2 | `GET /api/stats` — Return aggregated statistics: total count, counts by level, by source, and by category. |
| FR-05.3 | `POST /api/analyze` — Accept a JSON body `{"logs": [...]}` of raw log strings, analyze each, store results, and return them. |
| FR-05.4 | `POST /api/analyze/file` — Accept a file upload, parse it, analyze each line, store, and return results. (Local mode only.) |
| FR-05.5 | `POST /api/correlate` — Correlate all stored problem logs into an incident report and return it. |
| FR-05.6 | `GET /api/incidents` — List all stored incident reports, most recent first. |
| FR-05.7 | `POST /api/import` — Import results from an existing `analysis_results.json` file. (Local mode only.) |
| FR-05.8 | `DELETE /api/logs` — Delete all logs and incidents from the database. |
| FR-05.9 | All API responses SHALL include CORS headers allowing any origin. |

### FR-06: Dashboard

| ID | Requirement |
|----|-------------|
| FR-06.1 | The system SHALL provide a single-page HTML dashboard with a dark theme. |
| FR-06.2 | The dashboard SHALL display stat cards for total, critical, error, warning, info, and debug log counts. |
| FR-06.3 | The dashboard SHALL display a filterable table of analyzed logs showing: level (color-coded badge), source, category, summary, suggestion, and raw log (expandable on click). |
| FR-06.4 | The dashboard SHALL provide dropdown filters for level and category, and a text search input. (Local mode also has source filter.) |
| FR-06.5 | The dashboard SHALL display incident reports with severity badge, root cause, affected services, related lines, and recommended actions. |
| FR-06.6 | The dashboard SHALL have buttons for: Refresh, Correlate Incidents, Clear All, and Import JSON (local) or Set API URL (serverless). |
| FR-06.7 | The serverless dashboard SHALL allow the user to configure the API Gateway URL, persisted in `localStorage`. |

### FR-07: CLI

| ID | Requirement |
|----|-------------|
| FR-07.1 | `cli.py` SHALL accept an optional file path argument (default: `sample_logs.txt`). |
| FR-07.2 | The CLI SHALL print color-coded analysis results to the terminal for each log. |
| FR-07.3 | The CLI SHALL print a summary with counts per severity level. |
| FR-07.4 | The CLI SHALL automatically correlate problem logs and print the incident report. |
| FR-07.5 | The CLI SHALL save results to both `analysis_results.json` and `logs.db`. |

### FR-08: CloudWatch Integration (Serverless)

| ID | Requirement |
|----|-------------|
| FR-08.1 | The processor Lambda SHALL receive CloudWatch Logs subscription events (base64-encoded, gzipped JSON). |
| FR-08.2 | The processor SHALL filter out Lambda runtime noise messages: lines matching `START`, `END`, `REPORT`, `INIT_START`, `EXTENSION`, or internal processing info logs. |
| FR-08.3 | The system SHALL support subscribing to arbitrary CloudWatch log groups via CDK context parameter `log_group_names`. |
| FR-08.4 | A test generator Lambda SHALL produce sample logs at varied severity levels, automatically triggering the processor via a subscription filter on its own log group. |

---

## 3. Non-Functional Requirements

### NFR-01: Performance

| ID | Requirement |
|----|-------------|
| NFR-01.1 | The processor Lambda SHALL have a timeout of 5 minutes and 512 MB memory. |
| NFR-01.2 | The API Lambda SHALL have a timeout of 5 minutes and 512 MB memory. |
| NFR-01.3 | The test generator Lambda SHALL have a timeout of 30 seconds and 128 MB memory. |
| NFR-01.4 | DynamoDB tables SHALL use on-demand (PAY_PER_REQUEST) billing for automatic scaling. |

### NFR-02: AI Model Configuration

| ID | Requirement |
|----|-------------|
| NFR-02.1 | The system SHALL use Amazon Bedrock as the AI model provider via `ai_functions`. |
| NFR-02.2 | **Local mode** SHALL use the library's default model (configurable via `@ai_function(model=...)`). |
| NFR-02.3 | **Serverless mode** SHALL explicitly configure `BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")` (cross-region inference profile). |
| NFR-02.4 | The model configuration SHALL be centralized in a single `_MODEL` constant in `analyzer.py`, shared by all AI functions. |

### NFR-03: Security

| ID | Requirement |
|----|-------------|
| NFR-03.1 | Lambda execution roles SHALL follow least privilege: DynamoDB read/write on specific tables, Bedrock invoke on `*`. |
| NFR-03.2 | API Gateway SHALL enable CORS for all origins (demo/investigation scope). |
| NFR-03.3 | The S3 dashboard bucket SHALL have public read access with static website hosting enabled (demo scope). |
| NFR-03.4 | No API keys or secrets SHALL be hardcoded; AWS SDK SHALL use IAM role credentials. |

### NFR-04: Reliability

| ID | Requirement |
|----|-------------|
| NFR-04.1 | AI function failures SHALL be caught per-log; a single failure SHALL NOT prevent processing of remaining logs. |
| NFR-04.2 | The processor Lambda response SHALL include error count and last error message for debugging. |
| NFR-04.3 | Post-conditions SHALL retry with configurable `max_attempts` (3 for summarization and correlation, 2 for suggestion validation). |

### NFR-05: Deployability

| ID | Requirement |
|----|-------------|
| NFR-05.1 | The serverless stack SHALL be deployable via a single PowerShell script (`deploy.ps1`). |
| NFR-05.2 | The stack SHALL be fully destroyable via `destroy.ps1`, including all created resources. |
| NFR-05.3 | All AWS resources SHALL carry `owner` and `project` tags. |
| NFR-05.4 | All DynamoDB tables and S3 buckets SHALL have `RemovalPolicy.DESTROY` for clean teardown. |
| NFR-05.5 | The Lambda layer SHALL be built using `uv pip compile` (for dependency resolution targeting `manylinux2014_x86_64/Python 3.12`) followed by `pip install --only-binary :all: --no-deps`. |

### NFR-06: Technology Constraints

| ID | Requirement |
|----|-------------|
| NFR-06.1 | Python >= 3.12 is required. |
| NFR-06.2 | Local mode dependencies: `ai_functions`, `fastapi`, `uvicorn`. Managed via `uv`. |
| NFR-06.3 | Serverless Lambda dependencies: `ai_functions`, `pydantic`. Packaged as a Lambda Layer. |
| NFR-06.4 | Infrastructure as Code: AWS CDK (Python) with `aws-cdk-lib >= 2.150.0`. |
| NFR-06.5 | Node.js is required for the CDK CLI (`npx cdk`). |
| NFR-06.6 | The dashboard SHALL be a single static HTML file with no build step, no JavaScript framework, and inline CSS. |

### NFR-07: Observability

| ID | Requirement |
|----|-------------|
| NFR-07.1 | Lambda handlers SHALL log structured messages via Python `logging` at INFO level. |
| NFR-07.2 | The processor handler SHALL log: event count, source log group/stream, per-event analysis result, and final summary. |
| NFR-07.3 | The API handler SHALL log each incoming request method, path, and query parameters. |

---

## 4. Data Schemas

### LogAnalysis (Pydantic model)

```
log_level:   Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
summary:     str
suggestion:  str
category:    str
confidence:  Literal["high", "medium", "low"]
```

### IncidentReport (Pydantic model)

```
title:               str
root_cause:          str
affected_services:   list[str]
severity:            Literal["low", "medium", "high", "critical"]
recommended_actions: list[str]
related_log_lines:   list[int]
```

---

## 5. Sample Log Formats Supported

```
2024-01-15 10:23:45 [auth-service] User login successful for user_id=4521
2024-01-15T10:23:45Z ERROR Something failed
ERROR 2026-03-23 Connection refused to database primary-01
Plain text log line without any structured format
```
