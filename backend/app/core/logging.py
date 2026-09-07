import logging
from datetime import UTC, datetime


class ContextFormatter(logging.Formatter):
    """Compact structured formatter with optional investigation identifiers."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, UTC).isoformat()
        context = " ".join(
            f"{name}={getattr(record, name)}"
            for name in ("case_id", "evidence_id", "job_id")
            if getattr(record, name, None) is not None
        )
        suffix = f" {context}" if context else ""
        return (
            f"{timestamp} level={record.levelname} service={record.name}{suffix} "
            f"message={record.getMessage()}"
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ContextFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
