"""
File-based logging with daily rotation.

This module provides a logger configured with:
- Daily log file rotation (new file per day)
- Log files named: app-YYYY-MM-DD.log
- Console output for development
- Configurable log level from settings
"""
import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional

from app.config import settings


class DailyRotatingFileHandler(logging.FileHandler):
    """
    Custom file handler that creates log files with date in filename.
    Files are named: app-YYYY-MM-DD.log
    Rotates automatically at midnight to create a new file for the new day.
    """
    
    def __init__(self, log_dir: Path, backup_count: int = 30):
        """
        Initialize the handler with daily rotation.
        
        Args:
            log_dir: Directory where log files will be stored
            backup_count: Number of old log files to keep (default: 30 days)
        """
        self.log_dir = Path(log_dir)
        self.backup_count = backup_count
        self.current_date = datetime.now().date()
        
        # Create initial filename with today's date
        filename = self._get_filename_for_date(self.current_date)
        
        # Initialize parent with the dated filename
        super().__init__(
            filename=str(filename),
            mode='a',
            encoding='utf-8',
            delay=False
        )
    
    def _get_filename_for_date(self, date_obj) -> Path:
        """Get filename for a specific date."""
        date_str = date_obj.strftime("%Y-%m-%d")
        return self.log_dir / f"app-{date_str}.log"
    
    def _cleanup_old_logs(self):
        """Remove log files older than backup_count days."""
        if self.backup_count <= 0:
            return
        
        # Get all log files matching the pattern
        log_files = sorted(
            self.log_dir.glob("app-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Keep only the most recent backup_count files
        if len(log_files) > self.backup_count:
            for old_file in log_files[self.backup_count:]:
                try:
                    old_file.unlink()
                except Exception:
                    pass  # Ignore errors when deleting old files
    
    def _should_rollover(self):
        """Check if we should rollover to a new day."""
        return datetime.now().date() != self.current_date
    
    def emit(self, record):
        """
        Emit a log record, checking if we need to rollover first.
        """
        # Check if we need to rollover to a new day
        if self._should_rollover():
            self.doRollover()
        
        # Emit the record
        super().emit(record)
    
    def doRollover(self):
        """
        Create new file with new date in filename.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Update to current date
        self.current_date = datetime.now().date()
        
        # Get new filename for today
        new_filename = self._get_filename_for_date(self.current_date)
        
        # Update baseFilename
        self.baseFilename = str(new_filename)
        
        # Clean up old log files
        self._cleanup_old_logs()
        
        # Open new file
        if not self.delay:
            self.stream = self._open()


def setup_logger(
    name: str = "app",
    log_level: Optional[str] = None,
    log_dir: str = "logs",
    console_output: bool = True
) -> logging.Logger:
    """
    Set up a logger with daily file rotation and console output.
    
    Args:
        name: Logger name (default: "app")
        log_level: Logging level (default: from settings.LOG_LEVEL)
        log_dir: Directory for log files (default: "logs")
        console_output: Whether to output to console (default: True)
    
    Returns:
        Configured logger instance
    """
    # Get log level from parameter or settings
    level = log_level or settings.LOG_LEVEL
    log_level_value = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level_value)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with daily rotation
    # Log files will be named: app-YYYY-MM-DD.log
    # When a new day starts, a new file is created automatically
    file_handler = DailyRotatingFileHandler(log_path)
    file_handler.setLevel(log_level_value)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # Console handler (for development)
    if console_output:
        # Use a handler that can handle Unicode on Windows
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level_value)
        console_handler.setFormatter(formatter)
        # Set encoding to UTF-8 for console output if possible
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass  # Ignore if reconfiguration fails
        logger.addHandler(console_handler)
    
    return logger


# Create the default logger instance
logger = setup_logger(
    name="app",
    log_level=settings.LOG_LEVEL,
    log_dir="logs",
    console_output=True
)

__all__ = ["logger", "setup_logger"]
