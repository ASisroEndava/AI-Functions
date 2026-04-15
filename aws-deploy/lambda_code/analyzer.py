from typing import Literal

from pydantic import BaseModel

from ai_functions import ai_function
from ai_functions.types import PostConditionResult
from strands.models.bedrock import BedrockModel

# ---------------------------------------------------------------------------
# Serverless model configuration  (NFR-02.3 / NFR-02.4)
# Cross-region inference profile — the "us." prefix is required.
# ---------------------------------------------------------------------------

_MODEL = BedrockModel(model_id="us.anthropic.claude-3-haiku-20240307-v1:0")

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogAnalysis(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    summary: str
    suggestion: str
    category: str
    confidence: Literal["high", "medium", "low"]


class IncidentReport(BaseModel):
    title: str
    root_cause: str
    affected_services: list[str]
    severity: Literal["low", "medium", "high", "critical"]
    recommended_actions: list[str]
    related_log_lines: list[int]


# ---------------------------------------------------------------------------
# Post-condition helpers
# ---------------------------------------------------------------------------

def check_summary_length(summary: str):
    """Post-condition: summary must be at most 30 words."""
    word_count = len(summary.split())
    assert word_count <= 30, f"Summary has {word_count} words, max is 30"


def check_incident_has_actions(report: IncidentReport):
    """Post-condition: incident report must have at least one recommended action."""
    assert (
        report.recommended_actions and len(report.recommended_actions) >= 1
    ), "Incident report has no recommended actions"


# ---------------------------------------------------------------------------
# AI functions  (FR-02)
# ---------------------------------------------------------------------------

@ai_function(model=_MODEL)
def classify_severity(log_entry: str) -> LogLevel:
    """Classify the severity level of this log entry.

    Log entry: {log_entry}

    Analyze the log message and determine its severity level.
    Consider error indicators, warning signs, and the overall tone of the message."""


@ai_function(model=_MODEL)
def categorize_log(log_entry: str) -> str:
    """Categorize this log entry into exactly one category.

    Log entry: {log_entry}

    Available categories: authentication, networking, database, filesystem,
    performance, security, configuration, application, deployment

    Return ONLY the category name, nothing else."""


@ai_function(model=_MODEL, post_conditions=[check_summary_length], max_attempts=3)
def summarize_log(log_entry: str, severity: str, category: str) -> str:
    """Summarize this log entry in a single sentence of at most 30 words.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}

    Provide a concise, informative summary. Maximum 30 words. Do NOT exceed 30 words."""


@ai_function(model=_MODEL)
def suggest_fix(log_entry: str, severity: str, category: str, summary: str) -> str:
    """Suggest an actionable fix for this log entry.

    Log entry: {log_entry}
    Severity: {severity}
    Category: {category}
    Summary: {summary}

    Provide a specific, actionable suggestion to resolve or prevent this issue.
    Mention concrete steps, tools, or configurations an engineer should use."""


@ai_function(model=_MODEL)
def validate_suggestion_quality(result: LogAnalysis) -> PostConditionResult:
    """Evaluate whether this fix suggestion is actionable and specific.

    Log level: {result.log_level}
    Summary: {result.summary}
    Suggestion: {result.suggestion}
    Category: {result.category}

    Determine if the suggestion is specific enough to be actionable by an engineer.
    A good suggestion should mention specific steps, tools, or configurations."""


@ai_function(model=_MODEL, post_conditions=[check_incident_has_actions], max_attempts=3)
def correlate_logs(log_analyses: list[dict]) -> IncidentReport:
    """Correlate these problem logs into a single incident report.

    Problem logs:
    {log_analyses}

    Analyze all the logs together to:
    1. Identify a common title for the incident
    2. Determine the most likely root cause
    3. List all affected services
    4. Assess the overall severity (low/medium/high/critical)
    5. Suggest specific recommended actions to resolve the incident
    6. List the related log line numbers

    Every incident report MUST contain at least one recommended action."""


# ---------------------------------------------------------------------------
# Pipeline orchestration  (design doc section 2.2)
# ---------------------------------------------------------------------------

def analyze_log(log_entry: str) -> LogAnalysis:
    """Run the full AI analysis pipeline on a single log entry."""

    severity = classify_severity(log_entry)
    category = categorize_log(log_entry)
    summary = summarize_log(log_entry, severity, category)

    if severity in ("WARNING", "ERROR", "CRITICAL"):
        suggestion = suggest_fix(log_entry, severity, category, summary)
        result = LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion=suggestion,
            category=category,
            confidence="high",
        )
        for _attempt in range(2):
            validation = validate_suggestion_quality(result)
            if validation.passed:
                break
            suggestion = suggest_fix(log_entry, severity, category, summary)
            result = LogAnalysis(
                log_level=severity,
                summary=summary,
                suggestion=suggestion,
                category=category,
                confidence="high",
            )
        else:
            result = result.model_copy(update={"confidence": "low"})
        return result
    else:
        return LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion="N/A",
            category=category,
            confidence="high",
        )
