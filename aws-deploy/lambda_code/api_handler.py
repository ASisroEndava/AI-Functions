"""Lambda handler behind API Gateway — serves the REST API for the dashboard.

Routes:
  GET    /api/logs       → list analyzed logs (optional ?level= &category=)
  GET    /api/stats      → aggregated statistics
  POST   /api/analyze    → analyze raw logs on demand
  POST   /api/correlate  → correlate problem logs into an incident report
  GET    /api/incidents  → list incident reports
  DELETE /api/logs       → clear all data
"""
from __future__ import annotations

import json
import logging
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _response(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    qs = event.get("queryStringParameters") or {}

    logger.info("Request: %s %s params=%s", method, path, qs)

    try:
        if path == "/api/logs" and method == "GET":
            return _handle_get_logs(qs)
        elif path == "/api/logs" and method == "DELETE":
            return _handle_delete_logs()
        elif path == "/api/stats" and method == "GET":
            return _handle_get_stats()
        elif path == "/api/analyze" and method == "POST":
            body = json.loads(event.get("body") or "{}")
            return _handle_analyze(body)
        elif path == "/api/correlate" and method == "POST":
            return _handle_correlate()
        elif path == "/api/incidents" and method == "GET":
            return _handle_get_incidents()
        else:
            return _response(404, {"detail": f"Not found: {method} {path}"})
    except Exception as exc:
        logger.error("Unhandled error: %s\n%s", exc, traceback.format_exc())
        return _response(500, {"detail": str(exc)})


# ── Route handlers ───────────────────────────────────────────────────

def _handle_get_logs(qs: dict) -> dict:
    from dynamo_storage import query_logs

    level = qs.get("level")
    category = qs.get("category")
    limit = int(qs.get("limit", "200"))
    results = query_logs(log_level=level, category=category, limit=limit)
    return _response(200, results)


def _handle_get_stats() -> dict:
    from dynamo_storage import get_stats

    stats = get_stats()
    return _response(200, stats)


def _handle_analyze(body: dict) -> dict:
    from analyzer import analyze_log
    from dynamo_storage import put_logs_batch

    raw_logs = body.get("logs", [])
    if not raw_logs:
        return _response(400, {"detail": "No logs provided in body.logs"})

    results = []
    for idx, raw in enumerate(raw_logs, start=1):
        try:
            analysis = analyze_log(raw)
            entry = {
                "line": idx,
                "timestamp": "",
                "source": "api-upload",
                "raw": raw,
                **analysis.model_dump(),
            }
            results.append(entry)
        except Exception as exc:
            logger.warning("Failed to analyze log %d: %s", idx, exc)
            results.append({
                "line": idx,
                "timestamp": "",
                "source": "api-upload",
                "raw": raw,
                "log_level": "ERROR",
                "summary": f"Analysis failed: {exc}",
                "suggestion": "N/A",
                "category": "unknown",
                "confidence": "low",
            })

    put_logs_batch(results)
    return _response(200, {"processed": len(results), "results": results})


def _handle_correlate() -> dict:
    from analyzer import correlate_logs
    from dynamo_storage import query_logs, put_incident

    all_logs = query_logs(limit=500)
    problem_logs = [
        lg for lg in all_logs
        if lg.get("log_level") in ("WARNING", "ERROR", "CRITICAL")
    ]

    if not problem_logs:
        return _response(404, {"detail": "No problem logs to correlate"})

    analyses_for_ai = [
        {
            "line": lg.get("line", 0),
            "raw": lg.get("raw", ""),
            "severity": lg.get("log_level", "ERROR"),
            "category": lg.get("category", "unknown"),
            "summary": lg.get("summary", ""),
            "suggestion": lg.get("suggestion", ""),
        }
        for lg in problem_logs
    ]

    report = correlate_logs(analyses_for_ai)
    data = report.model_dump()
    put_incident(data)
    return _response(200, data)


def _handle_delete_logs() -> dict:
    from dynamo_storage import clear_all

    deleted = clear_all()
    return _response(200, {"deleted": deleted})


def _handle_get_incidents() -> dict:
    from dynamo_storage import list_incidents

    incidents = list_incidents()
    return _response(200, incidents)
