"""Logging configuration for the Backup & Restore Service.

This module configures a production-grade Python logger with:
- A custom TRACE level.
- Console output.
- Rotating file output under /app/logs (by default), including separate
  error-only and daily log files for easier triage.

The configuration is designed to be safe to call multiple times.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


TRACE_LEVEL_NUM = 5


def _install_trace_level() -> None:
    """Install the TRACE logging level and `Logger.trace` helper.

    Returns:
        None
    """

    if logging.getLevelName(TRACE_LEVEL_NUM) != "TRACE":
        logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

    if not hasattr(logging.Logger, "trace"):

        def trace(self: logging.Logger, message: str, *args, **kwargs) -> None:
            """Log a message with level TRACE.

            Args:
                message: Log message.
                *args: Positional args passed to logging.
                **kwargs: Keyword args passed to logging.

            Returns:
                None
            """

            if self.isEnabledFor(TRACE_LEVEL_NUM):
                self._log(TRACE_LEVEL_NUM, message, args, **kwargs)

        logging.Logger.trace = trace  # type: ignore[attr-defined]


def configure_logging(
    *,
    log_dir: str = "/app/logs",
    log_level: str = "INFO",
    debug: bool = False,
    log_filename: str = "backup-restore.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Configure application-wide logging.

    Args:
        log_dir: Directory where log files are stored.
        log_level: Root log level name (e.g. INFO, DEBUG, TRACE).
        debug: When True, defaults to DEBUG unless log_level explicitly overrides it.
        log_filename: Log file name (within log_dir).
        max_bytes: Rotate the log file after this size.
        backup_count: Number of rotated files to keep.

    Returns:
        None

    Raises:
        ValueError: When the provided log_level is invalid.
    """

    _install_trace_level()

    root = logging.getLogger()
    if getattr(root, "_backup_restore_logging_configured", False):
        return

    resolved_level_name = str(log_level or "").strip().upper()
    if not resolved_level_name:
        resolved_level_name = "DEBUG" if debug else "INFO"

    if resolved_level_name == "TRACE":
        resolved_level = TRACE_LEVEL_NUM
    else:
        resolved_level = getattr(logging, resolved_level_name, None)
        if not isinstance(resolved_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

    root.setLevel(resolved_level)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)
    console_handler._backup_restore_handler = True  # type: ignore[attr-defined]

    root.addHandler(console_handler)

    log_filename_path = Path(log_filename)
    error_filename = f"{log_filename_path.stem}.error{log_filename_path.suffix or '.log'}"
    daily_filename = f"{log_filename_path.stem}.day{log_filename_path.suffix or '.log'}"
    daily_error_filename = f"{log_filename_path.stem}.day.error{log_filename_path.suffix or '.log'}"

    log_path = Path(log_dir) / str(log_filename)
    error_log_path = Path(log_dir) / error_filename
    daily_log_path = Path(log_dir) / daily_filename
    daily_error_log_path = Path(log_dir) / daily_error_filename
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        file_handler._backup_restore_handler = True  # type: ignore[attr-defined]
        root.addHandler(file_handler)

        error_file_handler = RotatingFileHandler(
            filename=str(error_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        error_file_handler._backup_restore_handler = True  # type: ignore[attr-defined]
        root.addHandler(error_file_handler)

        daily_handler = TimedRotatingFileHandler(
            filename=str(daily_log_path),
            when="midnight",
            backupCount=backup_count,
            utc=True,
            encoding="utf-8",
        )
        daily_handler.suffix = "%Y-%m-%d"  # type: ignore[attr-defined]
        daily_handler.setLevel(resolved_level)
        daily_handler.setFormatter(formatter)
        daily_handler._backup_restore_handler = True  # type: ignore[attr-defined]
        root.addHandler(daily_handler)

        daily_error_handler = TimedRotatingFileHandler(
            filename=str(daily_error_log_path),
            when="midnight",
            backupCount=backup_count,
            utc=True,
            encoding="utf-8",
        )
        daily_error_handler.suffix = "%Y-%m-%d"  # type: ignore[attr-defined]
        daily_error_handler.setLevel(logging.ERROR)
        daily_error_handler.setFormatter(formatter)
        daily_error_handler._backup_restore_handler = True  # type: ignore[attr-defined]
        root.addHandler(daily_error_handler)
    except Exception:
        logging.getLogger(__name__).warning(
            "Failed to configure file logging under %s; continuing with console-only logging",
            log_dir,
        )

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    logging.captureWarnings(True)
    root._backup_restore_logging_configured = True  # type: ignore[attr-defined]


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger instance.

    Args:
        name: Logger name.

    Returns:
        logging.Logger: Logger instance.
    """

    return logging.getLogger(name or __name__)
