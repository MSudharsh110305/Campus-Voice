"""
Logging configuration with JSON and text format support.
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict
from pathlib import Path
from src.config.settings import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = None,
    level: str = None,
    log_file: str = None
) -> logging.Logger:
    """
    Setup logger with configured handlers.
    
    Args:
        name: Logger name (default: root)
        level: Log level (default: from settings)
        log_file: Log file path (default: from settings)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        formatter = ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    log_file_path = log_file or settings.LOG_FILE
    if log_file_path:
        # Create log directory if it doesn't exist
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        
        if settings.LOG_FORMAT == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any
):
    """
    Log message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context data
    """
    log_func = getattr(logger, level.lower())
    extra = {"extra_data": context}
    log_func(message, extra=extra)


# Setup default application logger
app_logger = setup_logger("campusvoice", settings.LOG_LEVEL, settings.LOG_FILE)


__all__ = [
    "setup_logger",
    "log_with_context",
    "app_logger",
    "JSONFormatter",
    "ColoredFormatter",
]
