import json
import logging
import sys

from app.core.logging_config import JsonFormatter


def make_record(message: str, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.realtime.poller",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


def test_format_produces_valid_json_with_expected_fields() -> None:
    formatter = JsonFormatter()
    record = make_record("Vehicle poll failed")

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "ERROR"
    assert payload["logger"] == "app.realtime.poller"
    assert payload["message"] == "Vehicle poll failed"
    assert "timestamp" in payload
    assert "exception" not in payload


def test_format_includes_exception_details_when_present() -> None:
    formatter = JsonFormatter()
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = make_record("Vehicle poll failed", exc_info=sys.exc_info())

    payload = json.loads(formatter.format(record))

    assert "RuntimeError" in payload["exception"]
    assert "boom" in payload["exception"]
