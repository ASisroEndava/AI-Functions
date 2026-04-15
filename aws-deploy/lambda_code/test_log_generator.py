import logging
import random
import time

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

SAMPLE_MESSAGES = {
    "DEBUG": [
        "Cache key user_session_4521 resolved in 2ms",
        "Connection pool stats: active=12 idle=38 max=50",
        "Health check passed for all downstream services",
    ],
    "INFO": [
        "User login successful for user_id=7823 from 192.168.1.105",
        "Deployment of auth-service v3.1.0 completed in 42s",
        "Scheduled backup of database primary-01 started",
        "OAuth token refresh successful for client_id=mobile-app",
    ],
    "WARNING": [
        "API response time exceeded 5s threshold for /api/search endpoint",
        "Disk usage on /data volume at 82% - approaching critical threshold",
        "SSL certificate for internal.api.example.com expires in 14 days",
        "Connection pool utilization at 85% - consider scaling database connections",
    ],
    "ERROR": [
        "Connection refused to database replica-03 at 10.0.2.15:5432",
        "OutOfMemoryError in worker thread pool-2-thread-14 - heap space exhausted",
        "Failed to process payment transaction txn_892341 - gateway timeout",
        "Configuration reload failed - invalid YAML syntax in app-config.yml",
    ],
    "CRITICAL": [
        "Database primary-01 unreachable - all write operations failing",
        "Security breach detected: unauthorized access to /admin/users endpoint from 203.0.113.42",
        "Filesystem /data is read-only - all write operations blocked",
    ],
}

LEVELS_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def handler(event, context):
    count = event.get("count", 10)
    severity_filter = event.get("severity")

    if severity_filter:
        available = {severity_filter: SAMPLE_MESSAGES.get(severity_filter, [])}
    else:
        available = SAMPLE_MESSAGES

    all_msgs = []
    for lvl, msgs in available.items():
        for msg in msgs:
            all_msgs.append((lvl, msg))

    if not all_msgs:
        return {"generated": 0, "error": f"No messages for severity={severity_filter}"}

    generated = 0
    for _ in range(count):
        lvl, msg = random.choice(all_msgs)
        logger.log(LEVELS_MAP[lvl], msg)
        generated += 1
        time.sleep(0.1)

    return {"generated": generated, "severity_filter": severity_filter}
