"""Logging configuration for the CPCC Enrollment API."""

import logging
import sys
from typing import Dict, Any
from datetime import datetime
import json

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Custom text formatter for human-readable logging."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging() -> None:
    """Set up logging configuration based on settings."""
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    # Set formatter based on configuration
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)
    
    def log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with additional context."""
        logger = self.logger
        if logger.isEnabledFor(level):
            # Create log record with extra fields
            record = logger.makeRecord(
                logger.name, level, __file__, 0, message, (), None
            )
            record.extra_fields = kwargs
            logger.handle(record)
    
    def log_request(self, method: str, url: str, **kwargs) -> None:
        """Log HTTP request with context."""
        self.log_with_context(
            logging.INFO,
            f"Making {method} request to {url}",
            method=method,
            url=url,
            **kwargs
        )
    
    def log_response(self, status_code: int, response_time: float, **kwargs) -> None:
        """Log HTTP response with context."""
        self.log_with_context(
            logging.INFO,
            f"Received response with status {status_code} in {response_time:.3f}s",
            status_code=status_code,
            response_time=response_time,
            **kwargs
        )
    
    def log_error(self, error: Exception, context: str = "", **kwargs) -> None:
        """Log error with context."""
        self.log_with_context(
            logging.ERROR,
            f"Error in {context}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            **kwargs
        )


# Initialize logging when module is imported
setup_logging()