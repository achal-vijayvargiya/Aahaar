"""
Logging configuration for file-based and console logging.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings


def setup_logger(name: str = "drassistent") -> logging.Logger:
    """
    Setup file-based logger with JSON formatting and rotation.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler for development (with colored output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        '%(levelname)s:     %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (10MB max, keep 5 backup files)
    try:
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(pathname)s:%(lineno)d]',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    # Log startup message
    logger.info("=" * 60)
    logger.info(f"Logger initialized: {name}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"Log File: {settings.LOG_FILE}")
    logger.info("=" * 60)
    
    return logger


# Create default logger instance
logger = setup_logger()

