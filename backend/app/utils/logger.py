"""
Logger compatibility layer.
Re-exports logger from app.legacy.utils.logger for backward compatibility.
"""
from app.legacy.utils.logger import logger, setup_logger

__all__ = ["logger", "setup_logger"]

