"""
Comprehensive logging configuration for the Nuggit application.

This module provides structured logging, log rotation, performance monitoring,
and configurable log levels across all components of the application.
"""

import os
import sys
import json
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import threading

from nuggit.util.timezone import utc_now_iso


@dataclass
class LogConfig:
    """Configuration for logging setup."""
    level: str = "INFO"
    format_type: str = "structured"  # "structured" or "simple"
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    log_directory: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_performance_logging: bool = True
    enable_audit_logging: bool = True
    sensitive_fields: list = None
    
    def __post_init__(self):
        if self.sensitive_fields is None:
            self.sensitive_fields = ["password", "token", "secret", "key", "authorization"]


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, sensitive_fields: list = None):
        super().__init__()
        self.sensitive_fields = sensitive_fields or []
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry
        log_entry = {
            "timestamp": utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": threading.current_thread().name,
            "process": os.getpid()
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'message'
            }:
                # Sanitize sensitive fields
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    value = "***REDACTED***"
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable formatter."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class PerformanceLogger:
    """Logger for performance metrics and timing."""
    
    def __init__(self, logger_name: str = "nuggit.performance"):
        self.logger = logging.getLogger(logger_name)
        self._timers: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation}_{threading.get_ident()}_{datetime.now().timestamp()}"
        with self._lock:
            self._timers[timer_id] = datetime.now().timestamp()
        return timer_id
    
    def end_timer(self, timer_id: str, operation: str, **kwargs):
        """End timing and log the duration."""
        with self._lock:
            start_time = self._timers.pop(timer_id, None)
        
        if start_time:
            duration = datetime.now().timestamp() - start_time
            self.logger.info(
                f"Performance metric: {operation}",
                extra={
                    "operation": operation,
                    "duration_seconds": round(duration, 4),
                    "timer_id": timer_id,
                    **kwargs
                }
            )
        else:
            self.logger.warning(f"Timer {timer_id} not found for operation {operation}")
    
    def log_metric(self, metric_name: str, value: Union[int, float], unit: str = "", **kwargs):
        """Log a performance metric."""
        self.logger.info(
            f"Metric: {metric_name} = {value} {unit}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                **kwargs
            }
        )


class AuditLogger:
    """Logger for audit events and security-related activities."""
    
    def __init__(self, logger_name: str = "nuggit.audit"):
        self.logger = logging.getLogger(logger_name)
    
    def log_access(self, user: str, resource: str, action: str, success: bool, **kwargs):
        """Log access attempts."""
        self.logger.info(
            f"Access: {user} {action} {resource} - {'SUCCESS' if success else 'FAILED'}",
            extra={
                "event_type": "access",
                "user": user,
                "resource": resource,
                "action": action,
                "success": success,
                **kwargs
            }
        )
    
    def log_data_change(self, user: str, table: str, operation: str, record_id: str, **kwargs):
        """Log data modification events."""
        self.logger.info(
            f"Data change: {user} {operation} {table}:{record_id}",
            extra={
                "event_type": "data_change",
                "user": user,
                "table": table,
                "operation": operation,
                "record_id": record_id,
                **kwargs
            }
        )
    
    def log_security_event(self, event_type: str, description: str, severity: str = "INFO", **kwargs):
        """Log security-related events."""
        log_level = getattr(logging, severity.upper(), logging.INFO)
        self.logger.log(
            log_level,
            f"Security event: {event_type} - {description}",
            extra={
                "event_type": "security",
                "security_event_type": event_type,
                "description": description,
                "severity": severity,
                **kwargs
            }
        )


def setup_logging(config: Optional[LogConfig] = None) -> Dict[str, Any]:
    """
    Set up comprehensive logging for the application.
    
    Args:
        config: Logging configuration. If None, uses default configuration.
        
    Returns:
        Dict containing logger instances and configuration info
    """
    if config is None:
        config = LogConfig()
    
    # Create logs directory if it doesn't exist
    log_dir = Path(config.log_directory)
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if config.format_type == "structured":
        formatter = StructuredFormatter(config.sensitive_fields)
    else:
        formatter = SimpleFormatter()
    
    handlers = []
    
    # Console handler
    if config.enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.level.upper()))
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # File handler with rotation
    if config.enable_file_logging:
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "nuggit.log",
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config.level.upper()))
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
        
        # Separate error log
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "nuggit_errors.log",
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        handlers.append(error_handler)
    
    # Add all handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Set up specialized loggers
    loggers = {}
    
    if config.enable_performance_logging:
        loggers["performance"] = PerformanceLogger()
    
    if config.enable_audit_logging:
        loggers["audit"] = AuditLogger()
    
    # Configure third-party library logging
    logging.getLogger("github").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging system initialized",
        extra={
            "config": asdict(config),
            "handlers_count": len(handlers),
            "log_directory": str(log_dir.absolute())
        }
    )
    
    return {
        "config": config,
        "loggers": loggers,
        "handlers": handlers,
        "log_directory": log_dir
    }


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger instance."""
    return PerformanceLogger()


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return AuditLogger()


# Context manager for timing operations
class LogTimer:
    """Context manager for timing operations with automatic logging."""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None, **kwargs):
        self.operation = operation
        self.logger = logger or get_performance_logger()
        self.kwargs = kwargs
        self.timer_id = None
    
    def __enter__(self):
        if isinstance(self.logger, PerformanceLogger):
            self.timer_id = self.logger.start_timer(self.operation)
        else:
            self.start_time = datetime.now().timestamp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.logger, PerformanceLogger) and self.timer_id:
            self.logger.end_timer(self.timer_id, self.operation, **self.kwargs)
        else:
            duration = datetime.now().timestamp() - self.start_time
            self.logger.info(
                f"Operation '{self.operation}' completed in {duration:.4f}s",
                extra={"operation": self.operation, "duration_seconds": duration, **self.kwargs}
            )


# Initialize logging with environment-based configuration
def init_logging_from_env():
    """Initialize logging based on environment variables."""
    config = LogConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format_type=os.getenv("LOG_FORMAT", "structured"),
        enable_file_logging=os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true",
        enable_console_logging=os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() == "true",
        log_directory=os.getenv("LOG_DIRECTORY", "logs"),
        enable_performance_logging=os.getenv("ENABLE_PERFORMANCE_LOGGING", "true").lower() == "true",
        enable_audit_logging=os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
    )
    
    return setup_logging(config)


# Request logging middleware for FastAPI
class RequestLoggingMiddleware:
    """Middleware to log HTTP requests and responses."""

    def __init__(self, app, logger_name: str = "nuggit.requests"):
        self.app = app
        self.logger = logging.getLogger(logger_name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request information
        request_info = {
            "method": scope["method"],
            "path": scope["path"],
            "query_string": scope["query_string"].decode(),
            "client": scope.get("client", ["unknown", 0])[0],
            "user_agent": None,
            "request_id": f"req_{datetime.now().timestamp()}_{os.getpid()}"
        }

        # Extract headers
        headers = dict(scope.get("headers", []))
        for name, value in headers.items():
            if name == b"user-agent":
                request_info["user_agent"] = value.decode()

        start_time = datetime.now().timestamp()

        # Log request start
        self.logger.info(
            f"Request started: {request_info['method']} {request_info['path']}",
            extra={
                "event_type": "request_start",
                **request_info
            }
        )

        # Capture response
        response_info = {"status_code": None, "response_size": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_info["status_code"] = message["status"]
            elif message["type"] == "http.response.body":
                response_info["response_size"] += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            response_info["status_code"] = 500
            response_info["error"] = str(e)
            raise
        finally:
            # Log request completion
            duration = datetime.now().timestamp() - start_time

            log_level = logging.INFO
            if response_info["status_code"] and response_info["status_code"] >= 400:
                log_level = logging.WARNING if response_info["status_code"] < 500 else logging.ERROR

            self.logger.log(
                log_level,
                f"Request completed: {request_info['method']} {request_info['path']} - "
                f"{response_info['status_code']} in {duration:.4f}s",
                extra={
                    "event_type": "request_complete",
                    "duration_seconds": round(duration, 4),
                    **request_info,
                    **response_info
                }
            )
