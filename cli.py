import json
import sys

from analyzer import LogAnalysis, analyze_log, correlate_logs
from log_reader import parse_log_file
from storage import init_db, insert_logs, insert_incident


LEVEL_COLORS = {
    "DEBUG": "\033[90m",     # gray
    "INFO": "\033[36m",      # cyan
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[35m",  # magenta
}
RESET = "\033[0m"


def print_analysis(line_number: int, raw: str, analysis: LogAnalysis) -> None:
    color = LEVEL_COLORS.get(analysis.log_level, "")
    level_badge = f"{color}[{analysis.log_level:^8}]{RESET}"

    print(f"\n{'─' * 70}")
    print(f"  Line {line_number}: {raw[:80]}{'...' if len(raw) > 80 else ''}")
    print(f"  Level:      {level_badge}")
    print(f"  Category:   \033[34m{analysis.category}{RESET}")
    print(f"  Summary:    {analysis.summary}")
    if analysis.suggestion != "N/A":
        print(f"  Suggestion: \033[33m{analysis.suggestion}{RESET}")


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else "sample_logs.txt"

    print(f"📂 Reading logs from: {log_path}\n")
    entries = parse_log_file(log_path)
    print(f"   Found {len(entries)} log entries.\n")

    results = []

    for entry in entries:
        print(f"⏳ Analyzing line {entry.line_number}...", end=" ", flush=True)
        try:
            analysis = analyze_log(entry.raw)
            print("✅")
            print_analysis(entry.line_number, entry.raw, analysis)
            results.append({
                "line": entry.line_number,
                "timestamp": entry.timestamp,
                "source": entry.source,
                "raw": entry.raw,
                **analysis.model_dump(),
            })
        except Exception as e:
            print(f"❌ Error: {e}")

    # Guardar resultados en JSON
    output_path = "analysis_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Guardar en SQLite
    init_db()
    insert_logs(results)

    print(f"\n{'═' * 70}")
    print(f"📊 Resumen: {len(results)} logs analizados")

    level_counts = {}
    for r in results:
        level_counts[r["log_level"]] = level_counts.get(r["log_level"], 0) + 1
    for level, count in sorted(level_counts.items()):
        color = LEVEL_COLORS.get(level, "")
        print(f"   {color}{level:>8}{RESET}: {count}")

    print(f"\n💾 Resultados guardados en: {output_path}")
    print(f"💾 Resultados guardados en: logs.db")

    # Correlación de logs problemáticos
    problem_logs = [
        r for r in results
        if r["log_level"] in ("WARNING", "ERROR", "CRITICAL")
    ]
    if problem_logs:
        print(f"\n🔗 Correlating {len(problem_logs)} problem logs...")
        try:
            analyses = [
                {
                    "line": r["line"],
                    "raw": r["raw"],
                    "severity": r["log_level"],
                    "category": r.get("category", "unknown"),
                    "summary": r["summary"],
                    "suggestion": r["suggestion"],
                }
                for r in problem_logs
            ]
            report = correlate_logs(analyses)
            insert_incident(report.model_dump())

            severity_color = {
                "low": "\033[90m", "medium": "\033[33m",
                "high": "\033[31m", "critical": "\033[35m",
            }
            sc = severity_color.get(report.severity, "")
            print(f"\n{'═' * 70}")
            print(f"🚨 Incident: {sc}{report.severity.upper()}{RESET} — {report.title}")
            print(f"   Root cause: {report.root_cause}")
            print(f"   Services:   {', '.join(report.affected_services)}")
            print(f"   Lines:      {report.related_log_lines}")
            print(f"   Actions:")
            for action in report.recommended_actions:
                print(f"     → {action}")
        except Exception as e:
            print(f"❌ Correlation failed: {e}")


if __name__ == "__main__":
    main()
