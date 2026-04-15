import base64
import gzip
import json
import logging
import re
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

NOISE_RE = re.compile(
    r"^(START |END |REPORT |INIT_START |EXTENSION |\[INFO\]\t.*\tProcessing )"
)


def handler(event, context):
    raw_data = event["awslogs"]["data"]
    decoded = gzip.decompress(base64.b64decode(raw_data))
    payload = json.loads(decoded)

    log_group = payload.get("logGroup", "unknown")
    log_stream = payload.get("logStream", "unknown")
    log_events = payload.get("logEvents", [])

    logger.info(
        "Received %d events from %s / %s", len(log_events), log_group, log_stream
    )

    from analyzer import analyze_log
    from dynamo_storage import put_log

    processed = 0
    errors = 0
    last_error = ""

    for idx, evt in enumerate(log_events, start=1):
        message = evt.get("message", "").strip()
        if not message:
            continue
        if NOISE_RE.match(message):
            continue

        try:
            analysis = analyze_log(message)
            entry = {
                "line": idx,
                "timestamp": evt.get("timestamp", ""),
                "source": log_group,
                "raw": message,
                "log_level": analysis.log_level,
                "summary": analysis.summary,
                "suggestion": analysis.suggestion,
                "category": analysis.category,
                "confidence": analysis.confidence,
            }
            put_log(entry)
            processed += 1
            logger.info(
                "Analyzed event: level=%s category=%s summary=%s",
                analysis.log_level,
                analysis.category,
                analysis.summary[:80],
            )
        except Exception as exc:
            errors += 1
            last_error = str(exc)
            logger.error("Failed to process event: %s\n%s", exc, traceback.format_exc())

    summary = {
        "processed": processed,
        "errors": errors,
        "total_events": len(log_events),
        "log_group": log_group,
        "log_stream": log_stream,
    }
    if last_error:
        summary["last_error"] = last_error

    logger.info("Processing complete: %s", json.dumps(summary))
    return summary
