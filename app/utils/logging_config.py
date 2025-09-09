"""
Structured logging configuration for the Legal Case File Manager.

This module provides comprehensive logging setup with:
- JSON formatted logs for production
- Human-readable logs for development
- Request correlation IDs
- Log rotation and different log levels
- Flask request lifecycle integration
"""

import json
import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime
from logging import Logger
from typing import Any, Dict, Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger

    JSONLOGGER_AVAILABLE = True
except ImportError:
    JSONLOGGER_AVAILABLE = False
from flask import Flask, g, has_request_context, request


class RequestContextFilter(logging.Filter):
    """Add request context information to log records."""

    def filter(self, record):
        """Add request-specific information to log records."""
        if has_request_context():
            # Add correlation ID
            record.correlation_id = getattr(g, "correlation_id", "no-request")
            record.request_method = getattr(request, "method", "UNKNOWN")
            record.request_path = getattr(request, "path", "unknown")
            record.remote_addr = getattr(request, "remote_addr", "unknown")
            record.user_agent = (
                request.headers.get("User-Agent", "unknown") if hasattr(request, "headers") else "unknown"
            )
        else:
            record.correlation_id = "no-request"
            record.request_method = "SYSTEM"
            record.request_path = "system"
            record.remote_addr = "system"
            record.user_agent = "system"

        return True


class CustomJSONFormatter(logging.Formatter):
    """Custom JSON formatter with additional fields."""

    def format(self, record):
        # Create log record dictionary
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.upper(),
            "name": record.name,
            "message": record.getMessage(),
            "service": "legal-case-manager",
            "version": "1.0.0",
        }

        # Add request context if available
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id
        if hasattr(record, "request_method"):
            log_record["request_method"] = record.request_method
        if hasattr(record, "request_path"):
            log_record["request_path"] = record.request_path
        if hasattr(record, "remote_addr"):
            log_record["remote_addr"] = record.remote_addr

        # Add any extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]:
                    if key not in log_record:  # Don't override existing fields
                        log_record[key] = value

        # Handle exception info
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for development console output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset_color = self.COLORS["RESET"]

        # Format the record
        formatted = super().format(record)

        # Add colors to the level name in the formatted string
        formatted = formatted.replace(record.levelname, f"{level_color}{record.levelname}{reset_color}")

        return formatted


class StructuredLogger:
    """Main structured logger class."""

    def __init__(self, name: str = "legal_case_manager"):
        self.name = name
        self.logger: Optional[Logger] = None
        self._configured = False

    def configure(self, app: Flask = None, **kwargs):
        """Configure the structured logger."""
        if self._configured:
            return self.logger

        # Get configuration from Flask app or kwargs
        if app:
            log_level = app.config.get("LOG_LEVEL", "INFO")
            log_format = app.config.get("LOG_FORMAT", "development")
            log_file = app.config.get("LOG_FILE", "logs/app.log")
            max_bytes = app.config.get("LOG_MAX_BYTES", 10 * 1024 * 1024)  # 10MB
            backup_count = app.config.get("LOG_BACKUP_COUNT", 5)
            enable_console = app.config.get("LOG_ENABLE_CONSOLE", True)
        else:
            log_level = kwargs.get("log_level", os.getenv("LOG_LEVEL", "INFO"))
            log_format = kwargs.get("log_format", os.getenv("LOG_FORMAT", "development"))
            log_file = kwargs.get("log_file", os.getenv("LOG_FILE", "logs/app.log"))
            max_bytes = kwargs.get("max_bytes", int(os.getenv("LOG_MAX_BYTES", "10485760")))
            backup_count = kwargs.get("backup_count", int(os.getenv("LOG_BACKUP_COUNT", "5")))
            enable_console = kwargs.get("enable_console", os.getenv("LOG_ENABLE_CONSOLE", "true").lower() == "true")

        # Create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Assert logger is not None for mypy
        assert self.logger is not None

        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Add request context filter
        context_filter = RequestContextFilter()

        # Configure based on format
        if log_format.lower() == "json":
            self._configure_json_logging(log_file, max_bytes, backup_count, enable_console, context_filter)
        else:
            self._configure_development_logging(log_file, max_bytes, backup_count, enable_console, context_filter)

        # Configure structlog if available
        if STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                    if log_format.lower() == "json"
                    else structlog.dev.ConsoleRenderer(),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )

        self._configured = True

        # Log configuration success
        self.logger.info(
            "Structured logging configured successfully",
            extra={
                "log_level": log_level,
                "log_format": log_format,
                "log_file": log_file,
                "enable_console": enable_console,
            },
        )

        return self.logger

    def _configure_json_logging(
        self,
        log_file: str,
        max_bytes: int,
        backup_count: int,
        enable_console: bool,
        context_filter: RequestContextFilter,
    ):
        """Configure JSON logging for production."""
        json_formatter = CustomJSONFormatter()

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(context_filter)
        assert self.logger is not None
        self.logger.addHandler(file_handler)

        # Console handler (JSON format)
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(json_formatter)
            console_handler.addFilter(context_filter)
            assert self.logger is not None
            self.logger.addHandler(console_handler)

    def _configure_development_logging(
        self,
        log_file: str,
        max_bytes: int,
        backup_count: int,
        enable_console: bool,
        context_filter: RequestContextFilter,
    ):
        """Configure human-readable logging for development."""
        # Development format with colors for console
        dev_format = (
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d "
            "[%(correlation_id)s] %(request_method)s %(request_path)s - %(message)s"
        )

        # File handler (no colors for file)
        file_formatter = logging.Formatter(dev_format)
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(context_filter)
        assert self.logger is not None
        self.logger.addHandler(file_handler)

        # Console handler with colors
        if enable_console:
            console_formatter = ColoredFormatter(dev_format)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(context_filter)
            assert self.logger is not None
            self.logger.addHandler(console_handler)

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance."""
        if not self._configured:
            raise RuntimeError("Logger not configured. Call configure() first.")

        if name:
            return logging.getLogger(f"{self.name}.{name}")

        if self.logger is None:
            raise RuntimeError("Logger not properly initialized.")
        return self.logger


# Global logger instance
structured_logger = StructuredLogger()


def setup_flask_logging(app: Flask):
    """Set up Flask application logging with request correlation."""

    # Configure the structured logger
    logger = structured_logger.configure(app)

    # Set Flask's logger to use our configuration
    app.logger.handlers.clear()
    app.logger.addHandler(logger.handlers[0] if logger.handlers else logging.NullHandler())
    app.logger.setLevel(logger.level)

    @app.before_request
    def before_request():
        """Generate correlation ID for each request."""
        g.correlation_id = str(uuid.uuid4())[:8]
        g.request_start_time = datetime.utcnow()

        # Log request start
        logger.info(
            "Request started",
            extra={
                "event": "request_start",
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "content_length": request.content_length,
            },
        )

    @app.after_request
    def after_request(response):
        """Log request completion."""
        duration = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000

        logger.info(
            "Request completed",
            extra={
                "event": "request_end",
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "content_length": response.content_length,
            },
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = g.correlation_id
        return response

    @app.teardown_appcontext
    def teardown_logging(exception=None):
        """Clean up logging context."""
        if exception:
            logger.error(
                "Request failed with exception",
                extra={
                    "event": "request_exception",
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                },
                exc_info=True,
            )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    # Auto-configure with defaults if not already configured
    if not structured_logger._configured:
        structured_logger.configure()
    return structured_logger.get_logger(name)


def log_database_operation(operation: str, table: Optional[str] = None, **kwargs):
    """Helper function to log database operations."""
    try:
        logger = get_logger("database")
        logger.info(
            f"Database operation: {operation}",
            extra={"event": "database_operation", "operation": operation, "table": table, **kwargs},
        )
    except Exception:
        # Fallback to basic logging if structured logging fails
        logging.getLogger("database").info(f"Database operation: {operation} on {table}")


def log_security_event(event_type: str, details: Dict[str, Any]):
    """Helper function to log security events."""
    try:
        logger = get_logger("security")
        logger.warning(
            f"Security event: {event_type}", extra={"event": "security_event", "event_type": event_type, **details}
        )
    except Exception:
        # Fallback to basic logging if structured logging fails
        logging.getLogger("security").warning(f"Security event: {event_type}")


def log_performance_metric(metric_name: str, value: float, unit: str = "ms", **kwargs):
    """Helper function to log performance metrics."""
    try:
        logger = get_logger("performance")
        logger.info(
            f"Performance metric: {metric_name}",
            extra={"event": "performance_metric", "metric_name": metric_name, "value": value, "unit": unit, **kwargs},
        )
    except Exception:
        # Fallback to basic logging if structured logging fails
        logging.getLogger("performance").info(f"Performance metric: {metric_name}={value}{unit}")


def log_business_event(event_type: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None, **kwargs):
    """Helper function to log business events."""
    try:
        logger = get_logger("business")
        logger.info(
            f"Business event: {event_type}",
            extra={
                "event": "business_event",
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                **kwargs,
            },
        )
    except Exception:
        # Fallback to basic logging if structured logging fails
        logging.getLogger("business").info(f"Business event: {event_type} on {entity_type}: {entity_id}")
