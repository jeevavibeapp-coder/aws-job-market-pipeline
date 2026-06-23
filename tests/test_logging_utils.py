"""Tests for structured logging + EMF metric emission."""

import json
import logging

from lambdas.common.logging_utils import JsonFormatter, emit_metric, get_logger


def test_json_formatter_emits_valid_json():
    fmt = JsonFormatter()
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    record.ctx = {"stage": "load", "rows": 5}
    out = json.loads(fmt.format(record))
    assert out["message"] == "hello"
    assert out["level"] == "INFO"
    assert out["stage"] == "load"
    assert out["rows"] == 5


def test_emit_metric_prints_emf(capsys):
    emit_metric("rows_loaded", 42, "Count", source="features")
    captured = json.loads(capsys.readouterr().out.strip())
    assert captured["rows_loaded"] == 42
    assert captured["source"] == "features"
    metric_def = captured["_aws"]["CloudWatchMetrics"][0]
    assert metric_def["Metrics"][0]["Name"] == "rows_loaded"
    assert metric_def["Dimensions"] == [["source"]]


def test_get_logger_is_idempotent():
    a = get_logger("dup")
    b = get_logger("dup")
    assert a is b
