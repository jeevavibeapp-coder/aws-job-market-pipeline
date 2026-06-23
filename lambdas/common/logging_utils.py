"""
Shared structured logging + CloudWatch EMF metrics helpers.

Every Lambda emits JSON-structured logs so CloudWatch Logs Insights can query
them, and emits custom metrics in the CloudWatch Embedded Metric Format (EMF)
so dashboards / alarms work without extra PutMetricData API calls.
"""

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime

_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "JobMarketPipeline")


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON for CloudWatch Logs Insights."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Merge any structured extras passed via logger.info(msg, extra={"ctx": {...}})
        ctx = getattr(record, "ctx", None)
        if isinstance(ctx, dict):
            payload.update(ctx)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a configured JSON logger (idempotent across warm invocations)."""
    logger = logging.getLogger(name)
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level)
    # AWS Lambda pre-installs a handler on the root logger; replace its formatter.
    root = logging.getLogger()
    if root.handlers:
        for h in root.handlers:
            h.setFormatter(JsonFormatter())
    elif not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def emit_metric(name: str, value: float, unit: str = "Count", **dimensions) -> None:
    """
    Emit a single custom metric using the CloudWatch Embedded Metric Format.

    Printing an EMF-shaped JSON blob to stdout is enough for CloudWatch to
    ingest it as a metric — no IAM PutMetricData permission required.
    """
    dims = [list(dimensions.keys())] if dimensions else []
    emf = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": _NAMESPACE,
                    "Dimensions": dims,
                    "Metrics": [{"Name": name, "Unit": unit}],
                }
            ],
        },
        name: value,
        **dimensions,
    }
    print(json.dumps(emf, default=str))


@contextmanager
def timed(logger: logging.Logger, stage: str, **dimensions):
    """
    Context manager that times a block, logs the duration, and emits a
    `<stage>_duration_ms` metric plus a success/failure metric.
    """
    start = time.perf_counter()
    try:
        yield
    except Exception:
        emit_metric(f"{stage}_errors", 1, "Count", **dimensions)
        logger.exception("Stage failed", extra={"ctx": {"stage": stage}})
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        emit_metric(f"{stage}_duration_ms", round(elapsed_ms, 2), "Milliseconds", **dimensions)
        logger.info(
            "Stage complete",
            extra={"ctx": {"stage": stage, "duration_ms": round(elapsed_ms, 2)}},
        )
