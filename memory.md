# Log Analyzer — Project Memory

Decisions, knowledge, and lessons learned. Keep this updated to avoid repeating mistakes.

---

## AI Library (`ai_functions`)

- **PyPI package name:** `strands-ai-functions` (`pip install strands-ai-functions`)
- **Import for decorator:** `from ai_functions import ai_function`
- **Import for post-condition type:** `from ai_functions.types import PostConditionResult`
- **Import for models:** `from strands.models.bedrock import BedrockModel` (models come from `strands`, NOT from `ai_functions`)
- **Decorator behavior:**
  - Docstring = prompt (supports `{param}` interpolation)
  - Return type annotation = output parsing (Literal, str, Pydantic BaseModel, etc.)
  - `post_conditions=[fn1, fn2]` + `max_attempts=N` = automatic retry on failure
- **Post-conditions:**
  - Deterministic checks: regular Python functions using `assert`
  - AI-evaluated checks: `@ai_function` returning `PostConditionResult`
- **Local mode:** `@ai_function()` — no `model` arg, uses library default (Bedrock)
- **Serverless mode:** `@ai_function(model=_MODEL)` — explicit model on every function
  - `_MODEL = BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")`
  - The `us.` prefix is **required** for cross-region inference profiles

## Documentation Updates

- All references in `specification.md`, `architecture.md`, `design.md` were changed from `strands-ai-functions` → `ai_functions`
- Import paths in `design.md` changed from `strands.models.bedrock` → `ai_functions.models.bedrock` (note: actual runtime import is still `from strands.models.bedrock`)

## Architecture Decisions

| Decision | Detail |
|----------|--------|
| **Dual mode** | Local (CLI + FastAPI + SQLite) and Serverless (Lambda + DynamoDB + API Gateway + S3) |
| **Separate `analyzer.py` per mode** | Local uses library defaults; serverless uses explicit model config. Avoids conditional logic. |
| **DynamoDB list fields** | Stored as JSON strings, not DynamoDB List type. Consistent with SQLite approach. |
| **Lazy imports in Lambda** | Heavy deps (`ai_functions`, `boto3` table resources) imported inside handler functions to reduce cold-start. |
| **Noise filter in processor** | Regex filters Lambda runtime messages (START/END/REPORT) to prevent recursive processing. |
| **S3 dashboard** | Public read, no CloudFront — acceptable for demo/investigation scope. |
| **DynamoDB billing** | PAY_PER_REQUEST — no capacity planning for demo workloads. |
| **Lambda Layer build** | `uv pip compile` (manylinux2014_x86_64/Python 3.12) → `pip install --only-binary :all: --no-deps` |
| **CDK tags** | `owner: ariel.sisro@endava.com`, `project: AI Functions investigation project` |

## File Structure

```
AI-Functions Generate from spec/
├── pyproject.toml
├── analyzer.py              # Local mode AI pipeline
├── log_reader.py            # Log parser
├── storage.py               # SQLite persistence
├── cli.py                   # CLI entry point
├── api.py                   # FastAPI REST API
├── dashboard.html           # Local dashboard
├── sample_logs.txt          # Test data
├── memory.md                # THIS FILE
├── IMPLEMENTATION_NOTES.md  # Spec interpretation & assumptions
│
├── aws-deploy/
│   ├── app.py               # CDK app entry
│   ├── cdk.json             # CDK config
│   ├── stack.py             # CDK stack (all resources)
│   ├── requirements.txt     # CDK deps
│   ├── deploy.ps1           # One-click deploy
│   ├── destroy.ps1          # One-click teardown
│   ├── README.md            # Deployment guide
│   ├── .gitignore
│   ├── lambda_code/
│   │   ├── analyzer.py      # Serverless AI pipeline (explicit model)
│   │   ├── cloudwatch_handler.py
│   │   ├── api_handler.py
│   │   ├── dynamo_storage.py
│   │   ├── test_log_generator.py
│   │   └── requirements.txt
│   └── dashboard/
│       └── index.html       # Serverless dashboard (S3)
│
└── documentation/
    ├── specification.md
    ├── architecture.md
    └── design.md
```

## Open Questions (Unresolved)

1. Is `@ai_function` thread-safe for concurrent FastAPI calls?
2. Exact `strands-ai-functions` version to pin?
3. Does `uv` need to be pre-installed? (`deploy.ps1` assumes it's on PATH)
4. ~~`cwlogs.LambdaDestination` import~~ — **RESOLVED**: confirmed it must be `from aws_cdk.aws_logs_destinations import LambdaDestination`

## Deployment Fixes (validated 2026-03-24)

All of these are already applied in the code/scripts but documented here to prevent re-discovery.

1. **`LambdaDestination` import** — `aws_cdk.aws_logs` does NOT have it. Use `from aws_cdk import aws_logs_destinations as cwlogs_dest` and then `cwlogs_dest.LambdaDestination(fn)`. Applies to `_cw_subscriptions()` and `_test_generator_lambda()` in `stack.py`.
2. **`$env:AWS_PROFILE`** — `deploy.ps1` sets `$env:AWS_PROFILE = "419466290453_AdministratorAccess"`. Without it CDK fails with "Unable to resolve AWS account".
3. **`$env:AWS_PAGER = ""`** — AWS CLI defaults to `cat` as pager on Windows, which doesn't exist. Set to empty.
4. **`$env:JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION = "1"`** — Suppresses noisy warning with Node.js 25+. Cosmetic only.
5. **PowerShell JSON quoting** — `aws lambda invoke --payload '{...}'` fails because PowerShell mangles quotes. Workaround: write JSON to file, use `fileb://payload.json`.
6. **SSO credentials expire** — Profile uses temporary session tokens. When expired, renew from AWS SSO portal → account 419466290453 → AdministratorAccess → "Command line or programmatic access" → paste into `%USERPROFILE%\.aws\credentials`.
7. **Bedrock model access** — Must be enabled in Bedrock Console → Model access → Anthropic → Claude 3.5 Haiku → Access granted. Otherwise Lambdas get `AccessDeniedException`.
8. **IAM for deploy** — CDK needs broad permissions (`cloudformation:*`, `s3:*`, `iam:*`, `lambda:*`, `dynamodb:*`, `apigateway:*`, `logs:*`, `bedrock:InvokeModel`, `ssm:*`, `ecr:*`, `sts:*`). Use `AdministratorAccess` for demo.
9. **`destroy.ps1` needs same env vars** — `AWS_PROFILE`, `AWS_PAGER`, `JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION` must be set in `destroy.ps1` just like `deploy.ps1`. Already applied.
10. **CDK cached credentials** — After renewing SSO creds, `aws sts get-caller-identity` may work but CDK still fails with `ExpiredToken`. Retry the CDK command — the second run picks up fresh creds. If persistent, delete `%USERPROFILE%\.cdk`.

## Deployed Stack Outputs (2026-03-24)

- **API Gateway:** `https://vb97md6jee.execute-api.us-east-1.amazonaws.com/prod/`
- **Dashboard:** `http://loganalyzerstack-dashboardsitebucketa33b04c8-ce9mfbkk9ysg.s3-website-us-east-1.amazonaws.com`
- **Processor Lambda:** `log-analyzer-cw-processor`
- **API Lambda:** `log-analyzer-api`
- **Test Generator:** `log-analyzer-test-generator`

## Lessons Learned

- The **pip package name** (`strands-ai-functions`) is different from the **import name** (`ai_functions`) — always check both.
- Large code blocks can trigger similarity filters in the edit tool — write incrementally in smaller chunks.
- Always verify library APIs against actual source/README before implementing, not just from docs that may be outdated.
- **Always test CDK imports locally** before deploying — `aws_cdk` submodule paths are not always intuitive.
- **PowerShell + AWS CLI JSON** is a known pain point — always use `fileb://` for payloads.
