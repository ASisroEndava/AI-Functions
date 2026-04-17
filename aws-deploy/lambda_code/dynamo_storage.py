import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

_ddb = boto3.resource("dynamodb")

LOGS_TABLE = os.environ.get("LOGS_TABLE", "log-analyzer-logs")
INCIDENTS_TABLE = os.environ.get("INCIDENTS_TABLE", "log-analyzer-incidents")


def _logs_table():
    return _ddb.Table(LOGS_TABLE)


def _incidents_table():
    return _ddb.Table(INCIDENTS_TABLE)


def _next_seq(count: int = 1) -> int:
    """Atomically increment the sequence counter and return the NEW value.

    Uses a special item in the logs table with id='_seq_counter'.
    For batch inserts, pass count > 1 to reserve a range.
    Returns the first seq number in the reserved range.
    """
    resp = _logs_table().update_item(
        Key={"id": "_seq_counter"},
        UpdateExpression="ADD seq_val :inc",
        ExpressionAttributeValues={":inc": count},
        ReturnValues="UPDATED_NEW",
    )
    new_val = int(resp["Attributes"]["seq_val"])
    return new_val - count + 1  # first seq in the reserved range


def put_log(entry: dict[str, Any]) -> dict[str, Any]:
    seq = _next_seq()
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": item_id,
        "seq": seq,
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
    }
    _logs_table().put_item(Item=item)
    return item


def put_logs_batch(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return []
    first_seq = _next_seq(len(entries))
    now = datetime.now(timezone.utc).isoformat()
    tbl = _logs_table()
    items = []
    with tbl.batch_writer() as batch:
        for i, entry in enumerate(entries):
            item = {
                "id": str(uuid.uuid4()),
                "seq": first_seq + i,
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
            }
            batch.put_item(Item=item)
            items.append(item)
    return items


def query_logs(
    log_level: str | None = None,
    category: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    tbl = _logs_table()

    if log_level:
        resp = tbl.query(
            IndexName="gsi-level-time",
            KeyConditionExpression=Key("log_level").eq(log_level),
            ScanIndexForward=False,
            Limit=limit,
        )
        return resp.get("Items", [])

    if category:
        resp = tbl.query(
            IndexName="gsi-category-time",
            KeyConditionExpression=Key("category").eq(category),
            ScanIndexForward=False,
            Limit=limit,
        )
        return resp.get("Items", [])

    items: list[dict] = []
    params: dict[str, Any] = {"Limit": limit}
    while True:
        resp = tbl.scan(**params)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp or len(items) >= limit:
            break
        params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    # Exclude the counter item from results
    items = [i for i in items if i.get("id") != "_seq_counter"]
    items.sort(key=lambda x: int(x.get("seq", 0) or 0), reverse=True)
    return items[:limit]


def get_stats() -> dict[str, Any]:
    tbl = _logs_table()
    items: list[dict] = []
    params: dict[str, Any] = {}
    while True:
        resp = tbl.scan(**params)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    items = [i for i in items if i.get("id") != "_seq_counter"]
    by_level: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in items:
        lvl = item.get("log_level", "UNKNOWN")
        by_level[lvl] = by_level.get(lvl, 0) + 1
        cat = item.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

    return {"total": len(items), "by_level": by_level, "by_category": by_category}


def clear_all() -> None:
    for tbl in (_logs_table(), _incidents_table()):
        scan = tbl.scan(ProjectionExpression="id")
        with tbl.batch_writer() as batch:
            for item in scan.get("Items", []):
                if item["id"] == "_seq_counter":
                    continue
                batch.delete_item(Key={"id": item["id"]})
        while "LastEvaluatedKey" in scan:
            scan = tbl.scan(
                ProjectionExpression="id",
                ExclusiveStartKey=scan["LastEvaluatedKey"],
            )
            with tbl.batch_writer() as batch:
                for item in scan.get("Items", []):
                    if item["id"] == "_seq_counter":
                        continue
                    batch.delete_item(Key={"id": item["id"]})


def put_incident(report: dict[str, Any]) -> str:
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": item_id,
        "title": report["title"],
        "root_cause": report["root_cause"],
        "affected_services": json.dumps(report["affected_services"]),
        "severity": report["severity"],
        "recommended_actions": json.dumps(report["recommended_actions"]),
        "related_log_lines": json.dumps(report["related_log_lines"]),
        "created_at": now,
    }
    _incidents_table().put_item(Item=item)
    return item_id


def list_incidents() -> list[dict[str, Any]]:
    tbl = _incidents_table()
    items: list[dict] = []
    params: dict[str, Any] = {}
    while True:
        resp = tbl.scan(**params)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    for item in items:
        for field in ("affected_services", "recommended_actions", "related_log_lines"):
            val = item.get(field, "[]")
            if isinstance(val, str):
                item[field] = json.loads(val)

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items
