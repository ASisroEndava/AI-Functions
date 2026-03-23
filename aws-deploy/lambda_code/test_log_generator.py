"""Test Lambda that generates sample log entries at various severity levels.

Invoke manually to produce CloudWatch log output that the processor Lambda
will pick up via the subscription filter.

    aws lambda invoke --function-name log-analyzer-test-generator out.json
"""

import json
import logging
import random
import time

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

SAMPLE_LOGS = [
    # DEBUG
    ("DEBUG", "Cache hit for session token abc-123, TTL remaining 245s"),
    ("DEBUG", "Loading configuration from /etc/app/config.yaml"),
    ("DEBUG", "DNS resolution for api.internal took 2ms"),
    # INFO
    ("INFO", "Application started successfully on port 8080"),
    ("INFO", "User user-42 authenticated via OAuth2 provider Google"),
    ("INFO", "Scheduled job 'cleanup-temp' completed in 1.2s, removed 34 files"),
    ("INFO", "Health check passed: database=ok, cache=ok, queue=ok"),
    # WARNING
    ("WARNING", "Connection pool utilization at 85% (17/20) for postgres-primary"),
    ("WARNING", "API response time degraded: p99=1200ms (threshold 500ms) on /api/search"),
    ("WARNING", "Disk usage on /data volume at 78%, approaching 80% alert threshold"),
    ("WARNING", "Rate limit approaching for client app-mobile: 450/500 requests in window"),
    # ERROR
    ("ERROR", "Failed to connect to Redis cluster at redis-001.cache.amazonaws.com:6379 - Connection refused after 3 retries"),
    ("ERROR", "Unhandled exception in payment processing: CardDeclinedException for order ORD-9981"),
    ("ERROR", "Database query timeout after 30s: SELECT * FROM orders WHERE status='pending' AND created_at < NOW() - INTERVAL '24 hours'"),
    ("ERROR", "S3 upload failed for object reports/2025-03-20/daily.csv: AccessDenied - bucket policy mismatch"),
    # CRITICAL
    ("CRITICAL", "Out of memory: container killed by OOM-killer, RSS=2048MB limit=2048MB, pod=api-server-7f8b9"),
    ("CRITICAL", "Primary database failover triggered: master node db-primary-01 unreachable for 60s, promoting replica db-replica-02"),
    ("CRITICAL", "SSL certificate for api.example.com expires in 24 hours - automatic renewal failed: ACME challenge DNS timeout"),
]


def handler(event, context):
    """Generate a batch of sample log entries."""
    count = event.get("count", 10) if isinstance(event, dict) else 10
    severity_filter = event.get("severity", None) if isinstance(event, dict) else None

    pool = SAMPLE_LOGS
    if severity_filter:
        pool = [s for s in SAMPLE_LOGS if s[0] == severity_filter.upper()]
        if not pool:
            pool = SAMPLE_LOGS

    selected = [random.choice(pool) for _ in range(count)]
    generated = []

    for level, message in selected:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{level} {ts} {message}"

        if level == "DEBUG":
            logger.debug(log_line)
        elif level == "INFO":
            logger.info(log_line)
        elif level == "WARNING":
            logger.warning(log_line)
        elif level == "ERROR":
            logger.error(log_line)
        elif level == "CRITICAL":
            logger.critical(log_line)

        generated.append(log_line)
        time.sleep(0.1)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Generated {len(generated)} log entries",
            "logs": generated,
        }),
    }
