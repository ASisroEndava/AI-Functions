from __future__ import annotations

from typing import Literal

from ai_functions import ai_function
from ai_functions.types import PostConditionResult
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogAnalysis(BaseModel):
    log_level: LogLevel
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
# Step 1: Classify severity
# ---------------------------------------------------------------------------

@ai_function()
def classify_severity(log_entry: str) -> LogLevel:
    """
    Classify the severity level of this log entry.
    Return exactly one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.

    Log entry:
    {log_entry}
    """


# ---------------------------------------------------------------------------
# Step 2: Categorize the log
# ---------------------------------------------------------------------------

@ai_function()
def categorize_log(log_entry: str) -> str:
    """
    Classify this log entry into exactly one category.
    Return only the category name, nothing else.

    Categories: authentication, networking, database, filesystem,
    performance, security, configuration, application, deployment

    Log entry:
    {log_entry}
    """


# ---------------------------------------------------------------------------
# Step 3: Summarize (context-aware — receives severity + category)
# ---------------------------------------------------------------------------

def check_summary_length(result: str) -> None:
    """El resumen no debe superar 30 palabras."""
    word_count = len(result.split())
    assert word_count <= 30, (
        f"Summary has {word_count} words, must be 30 or fewer."
    )


@ai_function(post_conditions=[check_summary_length], max_attempts=3)
def summarize_log(log_entry: str, severity: str, category: str) -> str:
    """
    Write a one-sentence summary (max 30 words) for this {severity} {category} log.
    Return only the summary sentence.

    Log entry:
    {log_entry}
    """


# ---------------------------------------------------------------------------
# Step 4: Suggest fix (only for WARNING/ERROR/CRITICAL)
# ---------------------------------------------------------------------------

@ai_function()
def suggest_fix(log_entry: str, severity: str, category: str, summary: str) -> str:
    """
    This is a {severity} log in the {category} category.
    Summary: {summary}

    Provide ONE short, specific, actionable suggestion to fix or mitigate
    this issue. Be concrete (e.g. mention specific config, commands, or code).

    Log entry:
    {log_entry}
    """


# ---------------------------------------------------------------------------
# Step 5: AI post-condition — validates suggestion quality
# ---------------------------------------------------------------------------

@ai_function
def validate_suggestion_quality(result: LogAnalysis) -> PostConditionResult:
    """
    Evaluate if the suggestion below is actionable and specific enough.
    A good suggestion mentions concrete steps (config changes, commands,
    code fixes, or monitoring actions).
    A bad suggestion is vague like "fix the error" or "check the logs".

    Suggestion: {result.suggestion}
    Category: {result.category}
    Summary: {result.summary}
    """


# ---------------------------------------------------------------------------
# Pipeline: compose all steps
# ---------------------------------------------------------------------------

def analyze_log(log_entry: str, line_number: int = 0) -> LogAnalysis:
    """Pipeline that composes multiple ai_functions to analyze a single log."""
    severity = classify_severity(log_entry)
    category = categorize_log(log_entry)
    summary = summarize_log(log_entry, severity, category)

    if severity in ("WARNING", "ERROR", "CRITICAL"):
        suggestion = suggest_fix(log_entry, severity, category, summary)

        # AI post-condition: validate suggestion quality, retry up to 2 times
        result = LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion=suggestion,
            category=category,
            confidence="high",
        )
        for attempt in range(2):
            validation = validate_suggestion_quality(result)
            if validation.passed:
                break
            # Re-generate with feedback from the validator
            suggestion = suggest_fix(log_entry, severity, category, summary)
            result = result.model_copy(update={"suggestion": suggestion})
        else:
            result = result.model_copy(update={"confidence": "low"})
    else:
        result = LogAnalysis(
            log_level=severity,
            summary=summary,
            suggestion="N/A",
            category=category,
            confidence="high",
        )

    return result


# ---------------------------------------------------------------------------
# Correlation: analyze groups of logs to detect incidents
# ---------------------------------------------------------------------------

def check_incident_has_actions(result: IncidentReport) -> None:
    """Un reporte de incidente debe tener al menos una acción recomendada."""
    assert len(result.recommended_actions) >= 1, (
        "Incident report must have at least one recommended action."
    )


@ai_function(post_conditions=[check_incident_has_actions], max_attempts=3)
def correlate_logs(log_analyses: list[dict]) -> IncidentReport:
    """
    Analyze these related log entries and determine if they represent
    a single incident or correlated failure.

    For each log you have: line number, raw log, severity, category,
    summary, and suggestion.

    Identify:
    - A short incident title
    - The root cause connecting these logs
    - Which services are affected
    - Overall severity (low, medium, high, critical)
    - Concrete recommended actions to resolve the incident
    - Which log line numbers are related to this incident

    Log analyses:
    {log_analyses}
    """
