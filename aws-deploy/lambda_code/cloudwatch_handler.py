"""Lambda handler: receives CloudWatch Logs subscription events,
runs each log message through the AI analysis pipeline, and
stores results in DynamoDB.

CloudWatch sends events as base64-encoded gzipped JSON payloads.
"""
from __future__ import annotations

import base64
import gzip
import json
import logging
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_RUNTIME_NOISE = re.compile(
    r"^(START |END |REPORT |INIT_START |EXTENSION |\[INFO\]\t.*\tProcessing )"
)

def _is_noise(msg: str) -> bool:
    """Return True for Lambda runtime / internal messages."""
    return bool(_RUNTIME_NOISE.match(msg))


def handler(event: dict, context) -> dict:
    from analyzer import analyze_log
    from dynamo_storage import put_log

    payload = event.get("awslogs", {}).get("data", "")
    if not payload:
        logger.warning("No awslogs.data in event — skipping")
        return {"statusCode": 200, "body": "no data"}

    raw_bytes = base64.b64decode(payload)
    decompressed = gzip.decompress(raw_bytes)
    log_data = json.loads(decompressed)

    log_group = log_data.get("logGroup", "unknown")
    log_stream = log_data.get("logStream", "unknown")
    log_events = log_data.get("logEvents", [])

    logger.info(
        "Processing %d events from %s / %s",
        len(log_events), log_group, log_stream,
    )

    processed = 0
    errors = 0

    for idx, log_event in enumerate(log_events):
        raw_message = log_event.get("message", "").strip()
        if not raw_message or _is_noise(raw_message):
            continue

        try:
            analysis = analyze_log(raw_message)
            entry = {
                "line": idx + 1,
                "timestamp": str(log_event.get("timestamp", "")),
                "source": f"{log_group}/{log_stream}",
                "raw": raw_message,
                **analysis.model_dump(),
            }
            put_log(entry)
            processed += 1
            logger.info("Analyzed event %d: %s", idx + 1, analysis.log_level)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            logger.error("Failed to analyze event %d: %s\n%s", idx + 1, exc, tb)
            errors += 1
            last_error = str(exc)

    summary = {
        "statusCode": 200,
        "body": json.dumps({
            "log_group": log_group,
            "total_events": len(log_events),
            "processed": processed,
            "errors": errors,
            "last_error": last_error if errors else None,
        }),
    }
    logger.info("Done: %s", summary["body"])
    return summary
