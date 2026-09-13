"""Application logging configuration.

Provides a shared ``logger`` instance and a ``setup_logger`` helper. Output is
sent to the console and to a rotating JSON log file (``logs/app.log``) using
``python-json-logger``. This module is re-exported by ``app.utils.logger`` for
backward compatibility with the rest of the codebase.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from pythonjsonlogger import jsonlogger

from app.config import settings

LOG_DIR = os.path.dirname(settings.LOG_FILE) or "logs"


def setup_logger(name: str = "drassistent", log_file: str = None, level: str = None) -> logging.Logger:
    """Create (or return) a configured logger.

    Args:
        name: Logger name.
        log_file: Optional path to the log file. Defaults to ``settings.LOG_FILE``.
        level: Optional log level name. Defaults to ``settings.LOG_LEVEL``.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    log_file = log_file or settings.LOG_FILE
    level = (level or settings.LOG_LEVEL).upper()

    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(level)

    # Avoid attaching duplicate handlers if the logger is already configured.
    if logger_instance.handlers:
        return logger_instance

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger_instance.addHandler(console_handler)

    try:
        os.makedirs(os.path.dirname(log_file) or LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(
            jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        )
        logger_instance.addHandler(file_handler)
    except OSError:
        # File logging is best-effort; console logging still works.
        pass

    logger_instance.propagate = False
    return logger_instance


logger = setup_logger()

__all__ = ["logger", "setup_logger"]
