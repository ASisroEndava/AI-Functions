from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DB_PATH = Path("logs.db")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    with get_db(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line INTEGER,
                timestamp TEXT,
                source TEXT,
                raw TEXT,
                log_level TEXT NOT NULL,
                summary TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_level ON logs (log_level)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_source ON logs (source)
        """)


def insert_log(conn: sqlite3.Connection, log: dict) -> int:
    cursor = conn.execute(
        """
        INSERT INTO logs (line, timestamp, source, raw, log_level, summary, suggestion)
        VALUES (:line, :timestamp, :source, :raw, :log_level, :summary, :suggestion)
        """,
        log,
    )
    return cursor.lastrowid


def insert_logs(logs: list[dict], db_path: Path = DB_PATH) -> int:
    with get_db(db_path) as conn:
        for log in logs:
            insert_log(conn, log)
    return len(logs)


def query_logs(
    db_path: Path = DB_PATH,
    log_level: str | None = None,
    source: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: dict = {}

    if log_level:
        conditions.append("log_level = :log_level")
        params["log_level"] = log_level.upper()

    if source:
        conditions.append("source = :source")
        params["source"] = source

    if search:
        conditions.append("(raw LIKE :search OR summary LIKE :search)")
        params["search"] = f"%{search}%"

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    params["limit"] = limit
    params["offset"] = offset

    with get_db(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM logs {where} ORDER BY id DESC LIMIT :limit OFFSET :offset",
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats(db_path: Path = DB_PATH) -> dict:
    with get_db(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        levels = conn.execute(
            "SELECT log_level, COUNT(*) as count FROM logs GROUP BY log_level ORDER BY count DESC"
        ).fetchall()
        sources = conn.execute(
            "SELECT source, COUNT(*) as count FROM logs GROUP BY source ORDER BY count DESC"
        ).fetchall()

    return {
        "total": total,
        "by_level": {row["log_level"]: row["count"] for row in levels},
        "by_source": {row["source"]: row["count"] for row in sources},
    }


def clear_logs(db_path: Path = DB_PATH) -> int:
    with get_db(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        conn.execute("DELETE FROM logs")
    return count
