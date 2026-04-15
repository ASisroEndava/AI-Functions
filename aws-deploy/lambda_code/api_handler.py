import json
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
    "Content-Type": "application/json",
}


def _resp(status_code: int, body) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


def handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    qs = event.get("queryStringParameters") or {}

    logger.info("Request: %s %s params=%s", method, path, json.dumps(qs))

    try:
        if method == "OPTIONS":
            return _resp(200, {})

        if path == "/api/logs" and method == "GET":
            return _handle_get_logs(qs)
        if path == "/api/logs" and method == "DELETE":
            return _handle_delete_logs()
        if path == "/api/stats" and method == "GET":
            return _handle_stats()
        if path == "/api/analyze" and method == "POST":
            return _handle_analyze(event)
        if path == "/api/correlate" and method == "POST":
            return _handle_correlate()
        if path == "/api/incidents" and method == "GET":
            return _handle_incidents()

        return _resp(404, {"detail": f"Not found: {method} {path}"})

    except Exception as exc:
        logger.error("Unhandled error: %s\n%s", exc, traceback.format_exc())
        return _resp(500, {"detail": str(exc)})


def _handle_get_logs(qs: dict) -> dict:
    from dynamo_storage import query_logs

    level = qs.get("level")
    category = qs.get("category")
    limit = int(qs.get("limit", "500"))
    items = query_logs(log_level=level, category=category, limit=limit)
    return _resp(200, items)


def _handle_delete_logs() -> dict:
    from dynamo_storage import clear_all

    clear_all()
    return _resp(200, {"status": "cleared"})


def _handle_stats() -> dict:
    from dynamo_storage import get_stats

    return _resp(200, get_stats())


def _handle_analyze(event: dict) -> dict:
    from analyzer import analyze_log
    from dynamo_storage import put_logs_batch

    body = json.loads(event.get("body", "{}"))
    raw_logs = body.get("logs", [])

    results = []
    errors = 0
    for i, raw_line in enumerate(raw_logs, start=1):
        try:
            analysis = analyze_log(raw_line)
            entry = {
                "line": i,
                "timestamp": "",
                "source": "",
                "raw": raw_line,
                "log_level": analysis.log_level,
                "summary": analysis.summary,
                "suggestion": analysis.suggestion,
                "category": analysis.category,
                "confidence": analysis.confidence,
            }
            results.append(entry)
        except Exception:
            errors += 1
            results.append({
                "line": i,
                "timestamp": "",
                "source": "",
                "raw": raw_line,
                "log_level": "ERROR",
                "summary": "Analysis failed",
                "suggestion": "Retry analysis",
                "category": "unknown",
                "confidence": "low",
            })

    if results:
        put_logs_batch(results)

    return _resp(200, {"results": results, "errors": errors})


def _handle_correlate() -> dict:
    from analyzer import correlate_logs
    from dynamo_storage import put_incident, query_logs

    all_logs = query_logs(limit=500)
    problem = [
        l for l in all_logs if l.get("log_level") in ("WARNING", "ERROR", "CRITICAL")
    ]
    if not problem:
        return _resp(400, {"detail": "No problem logs to correlate"})

    # Include seq numbers so the AI can reference them in related_log_lines
    for log in problem:
        log["line"] = int(log.get("seq", 0) or 0)

    incident = correlate_logs(problem)
    incident_dict = incident.model_dump()
    put_incident(incident_dict)
    return _resp(200, incident_dict)


def _handle_incidents() -> dict:
    from dynamo_storage import list_incidents

    return _resp(200, list_incidents())
