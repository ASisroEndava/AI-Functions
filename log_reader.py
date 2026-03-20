from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RawLogEntry:
    line_number: int
    raw: str
    timestamp: str = ""
    source: str = ""


def parse_log_file(path: str | Path) -> list[RawLogEntry]:
    """Lee un archivo de logs y devuelve una lista de entradas parseadas.

    Soporta formatos comunes como:
      2024-01-15 10:23:45 [service] Some message
      2024-01-15T10:23:45Z ERROR Something failed
      Plain text log lines (sin timestamp)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    entries: list[RawLogEntry] = []
    timestamp_pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*)\s+"
    )
    source_pattern = re.compile(r"\[([^\]]+)\]")

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        entry = RawLogEntry(line_number=i, raw=line)

        ts_match = timestamp_pattern.match(line)
        if ts_match:
            entry.timestamp = ts_match.group(1)

        src_match = source_pattern.search(line)
        if src_match:
            entry.source = src_match.group(1)

        entries.append(entry)

    return entries
