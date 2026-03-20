from typing import Literal

from ai_functions import ai_function
from ai_functions.types import PostConditionResult
from pydantic import BaseModel


class LogAnalysis(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    summary: str
    suggestion: str


def check_suggestion_consistency(result: LogAnalysis) -> None:
    """Si el log es INFO o DEBUG, suggestion debe ser N/A."""
    if result.log_level in ("DEBUG", "INFO"):
        assert result.suggestion == "N/A", (
            f"Log level is {result.log_level}, suggestion should be 'N/A' "
            f"but got: '{result.suggestion}'"
        )


def check_summary_length(result: LogAnalysis) -> None:
    """El resumen no debe superar 30 palabras."""
    word_count = len(result.summary.split())
    assert word_count <= 30, (
        f"Summary has {word_count} words, must be 30 or fewer."
    )


@ai_function(
    post_conditions=[check_suggestion_consistency, check_summary_length],
    max_attempts=3,
)
def analyze_log(log_entry: str) -> LogAnalysis:
    """
    Analyze the following log entry and return structured data.

    Rules:
    - log_level: classify as DEBUG, INFO, WARNING, ERROR, or CRITICAL
    - summary: one sentence (max 30 words) describing what happened
    - suggestion: if the log indicates a problem (WARNING, ERROR, CRITICAL),
      provide a short actionable suggestion to fix it.
      If the log is DEBUG or INFO, set suggestion to exactly "N/A"

    Log entry:
    {log_entry}
    """
