from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from analyzer import LogAnalysis, IncidentReport, analyze_log, correlate_logs
from log_reader import parse_log_file
from storage import init_db, insert_logs, query_logs, get_stats, clear_logs, insert_incident, query_incidents

logger = logging.getLogger(__name__)

app = FastAPI(title="Log Analyzer API", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# --- Schemas ---

class LogEntry(BaseModel):
    id: int | None = None
    line: int
    timestamp: str
    source: str
    raw: str
    log_level: str
    summary: str
    suggestion: str
    category: str = "unknown"
    confidence: str = "high"
    created_at: str | None = None


class AnalyzeRequest(BaseModel):
    logs: list[str]


class AnalyzeResponse(BaseModel):
    processed: int
    results: list[LogEntry]


class StatsResponse(BaseModel):
    total: int
    by_level: dict[str, int]
    by_source: dict[str, int]
    by_category: dict[str, int] = {}


class IncidentEntry(BaseModel):
    id: int | None = None
    title: str
    root_cause: str
    affected_services: list[str]
    severity: str
    recommended_actions: list[str]
    related_log_lines: list[int]
    created_at: str | None = None


# --- Endpoints ---

@app.get("/api/logs", response_model=list[LogEntry])
def list_logs(
    level: str | None = Query(None, description="Filter by log level"),
    source: str | None = Query(None, description="Filter by source"),
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in raw log or summary"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista logs procesados con filtros opcionales."""
    return query_logs(log_level=level, source=source, category=category, search=search, limit=limit, offset=offset)


@app.get("/api/stats", response_model=StatsResponse)
def stats():
    """Estadísticas generales de los logs."""
    return get_stats()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_logs(request: AnalyzeRequest):
    """Analiza una lista de logs crudos y guarda los resultados."""
    results = []
    for i, raw_log in enumerate(request.logs, start=1):
        try:
            analysis = analyze_log(raw_log)
            entry = {
                "line": i,
                "timestamp": "",
                "source": "",
                "raw": raw_log,
                **analysis.model_dump(),
            }
            results.append(entry)
        except Exception as e:
            results.append({
                "line": i,
                "timestamp": "",
                "source": "",
                "raw": raw_log,
                "log_level": "ERROR",
                "summary": f"Failed to analyze: {e}",
                "suggestion": "N/A",
            })

    insert_logs(results)
    return AnalyzeResponse(processed=len(results), results=results)


@app.post("/api/analyze/file", response_model=AnalyzeResponse)
async def analyze_file(file: UploadFile = File(...)):
    """Sube un archivo de logs, lo analiza y guarda los resultados."""
    content = await file.read()
    tmp_path = Path(f"_upload_{file.filename}")
    tmp_path.write_bytes(content)

    try:
        entries = parse_log_file(tmp_path)
        results = []
        for entry in entries:
            try:
                analysis = analyze_log(entry.raw)
                result = {
                    "line": entry.line_number,
                    "timestamp": entry.timestamp,
                    "source": entry.source,
                    "raw": entry.raw,
                    **analysis.model_dump(),
                }
                results.append(result)
            except Exception as e:
                results.append({
                    "line": entry.line_number,
                    "timestamp": entry.timestamp,
                    "source": entry.source,
                    "raw": entry.raw,
                    "log_level": "ERROR",
                    "summary": f"Failed to analyze: {e}",
                    "suggestion": "N/A",
                })

        insert_logs(results)
        return AnalyzeResponse(processed=len(results), results=results)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/import")
def import_json(path: str = Query(..., description="Path to analysis_results.json")):
    """Importa resultados desde un archivo JSON existente (ej: generado por cli.py)."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    count = insert_logs(data)
    return {"imported": count}


@app.delete("/api/logs")
def delete_logs():
    """Elimina todos los logs de la base de datos."""
    count = clear_logs()
    return {"deleted": count}


@app.post("/api/correlate", response_model=IncidentEntry)
def correlate():
    """Analiza todos los logs WARNING/ERROR/CRITICAL y genera un reporte de incidente."""
    logs = query_logs(limit=500)
    problem_logs = [
        l for l in logs
        if l["log_level"] in ("WARNING", "ERROR", "CRITICAL")
    ]
    if not problem_logs:
        raise HTTPException(status_code=404, detail="No problem logs to correlate")

    analyses = [
        {
            "line": l["line"],
            "raw": l["raw"],
            "severity": l["log_level"],
            "category": l.get("category", "unknown"),
            "summary": l["summary"],
            "suggestion": l["suggestion"],
        }
        for l in problem_logs
    ]
    report = correlate_logs(analyses)
    data = report.model_dump()
    insert_incident(data)
    return data


@app.get("/api/incidents", response_model=list[IncidentEntry])
def list_incidents():
    """Lista todos los reportes de incidentes."""
    return query_incidents()


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Sirve el dashboard web."""
    html_path = Path("dashboard.html").resolve()
    if not html_path.exists():
        html_path = Path(__file__).resolve().parent / "dashboard.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
