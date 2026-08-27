import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Formats log records as one JSON object per line, instead of a plain
    text/traceback dump — so a log aggregator (CloudWatch, Datadog, etc.)
    can parse fields programmatically rather than scraping text.

    Scoped to this application's own loggers (anything under app.*, e.g.
    the poller's failure logs); Uvicorn's own request-access logs keep
    their default format, since reformatting a third-party library's
    logging is a separate concern from this app's own observability.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    app_logger = logging.getLogger("app")
    app_logger.handlers = [handler]
    app_logger.setLevel(level)
    app_logger.propagate = False
