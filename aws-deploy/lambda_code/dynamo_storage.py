"""DynamoDB storage layer for the log analyzer Lambda functions.

Replaces the SQLite-based storage.py for the serverless deployment.
Tables are configured via environment variables LOGS_TABLE and INCIDENTS_TABLE.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

_ddb = boto3.resource("dynamodb")

LOGS_TABLE_NAME = os.environ.get("LOGS_TABLE", "log-analyzer-logs")
INCIDENTS_TABLE_NAME = os.environ.get("INCIDENTS_TABLE", "log-analyzer-incidents")


def _logs_table():
    return _ddb.Table(LOGS_TABLE_NAME)


def _incidents_table():
    return _ddb.Table(INCIDENTS_TABLE_NAME)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Logs ─────────────────────────────────────────────────────────────

def put_log(log_entry: dict) -> str:
    """Insert a single analyzed log. Returns the generated id."""
    item_id = str(uuid.uuid4())
    item = {
        "id": item_id,
        "line": log_entry.get("line", 0),
        "timestamp": log_entry.get("timestamp", ""),
        "source": log_entry.get("source", ""),
        "raw": log_entry.get("raw", ""),
        "log_level": log_entry["log_level"],
        "summary": log_entry["summary"],
        "suggestion": log_entry["suggestion"],
        "category": log_entry.get("category", "unknown"),
        "confidence": log_entry.get("confidence", "high"),
        "created_at": _now_iso(),
    }
    _logs_table().put_item(Item=item)
    return item_id


def put_logs_batch(entries: list[dict]) -> int:
    """Insert multiple logs in batch. Returns count written."""
    table = _logs_table()
    now = _now_iso()
    with table.batch_writer() as writer:
        for entry in entries:
            writer.put_item(Item={
                "id": str(uuid.uuid4()),
                "line": entry.get("line", 0),
                "timestamp": entry.get("timestamp", ""),
                "source": entry.get("source", ""),
                "raw": entry.get("raw", ""),
                "log_level": entry["log_level"],
                "summary": entry["summary"],
                "suggestion": entry["suggestion"],
                "category": entry.get("category", "unknown"),
                "confidence": entry.get("confidence", "high"),
                "created_at": now,
            })
    return len(entries)


def query_logs(
    log_level: str | None = None,
    category: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Query logs, optionally filtering by level or category via GSIs."""
    table = _logs_table()

    if log_level:
        resp = table.query(
            IndexName="gsi-level-time",
            KeyConditionExpression=Key("log_level").eq(log_level.upper()),
            ScanIndexForward=False,
            Limit=limit,
        )
        return resp.get("Items", [])

    if category:
        resp = table.query(
            IndexName="gsi-category-time",
            KeyConditionExpression=Key("category").eq(category),
            ScanIndexForward=False,
            Limit=limit,
        )
        return resp.get("Items", [])

    # Full scan (no filter) — fine for demo/test workloads
    resp = table.scan(Limit=limit)
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def get_stats() -> dict:
    """Aggregate stats by scanning the logs table."""
    table = _logs_table()
    items = []
    scan_kwargs: dict = {}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    by_level: dict[str, int] = {}
    by_source: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in items:
        lv = item.get("log_level", "UNKNOWN")
        by_level[lv] = by_level.get(lv, 0) + 1
        src = item.get("source", "")
        if src:
            by_source[src] = by_source.get(src, 0) + 1
        cat = item.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total": len(items),
        "by_level": by_level,
        "by_source": by_source,
        "by_category": by_category,
    }


def clear_all() -> int:
    """Delete every item in both tables. Returns deleted log count."""
    deleted = 0
    for tbl_fn in [_logs_table, _incidents_table]:
        table = tbl_fn()
        scan = table.scan(ProjectionExpression="id")
        with table.batch_writer() as writer:
            for item in scan.get("Items", []):
                writer.delete_item(Key={"id": item["id"]})
                deleted += 1
    return deleted


# ── Incidents ────────────────────────────────────────────────────────

def put_incident(report: dict) -> str:
    """Insert an incident report. Returns the generated id."""
    item_id = str(uuid.uuid4())
    _incidents_table().put_item(Item={
        "id": item_id,
        "title": report["title"],
        "root_cause": report["root_cause"],
        "affected_services": json.dumps(report["affected_services"]),
        "severity": report["severity"],
        "recommended_actions": json.dumps(report["recommended_actions"]),
        "related_log_lines": json.dumps(report["related_log_lines"]),
        "created_at": _now_iso(),
    })
    return item_id


def list_incidents() -> list[dict]:
    """Return all incidents, most recent first."""
    resp = _incidents_table().scan()
    items = resp.get("Items", [])
    for item in items:
        for field in ("affected_services", "recommended_actions", "related_log_lines"):
            if isinstance(item.get(field), str):
                item[field] = json.loads(item[field])
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items
