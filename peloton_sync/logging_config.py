"""Logging configuration for the Peloton Data Sync application."""

import logging
import sys
from typing import Dict, Any
import structlog
from structlog.stdlib import LoggerFactory
from colorama import init as colorama_init, Fore, Style

from .config import get_config

# Initialize colorama for cross-platform colored output
colorama_init()


def setup_logging() -> None:
    """Set up structured logging for the application."""
    app_config, _, _ = get_config()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _get_renderer(app_config.log_format),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, app_config.log_level.upper()),
    )
    
    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _get_renderer(log_format: str):
    """Get the appropriate log renderer based on format."""
    if log_format.lower() == "json":
        return structlog.processors.JSONRenderer()
    else:
        return _colored_console_renderer


def _colored_console_renderer(logger, method_name, event_dict):
    """Custom console renderer with colors."""
    level = event_dict.get("level", "").upper()
    timestamp = event_dict.get("timestamp", "")
    logger_name = event_dict.get("logger", "")
    message = event_dict.get("event", "")
    
    # Color mapping for log levels
    level_colors = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }
    
    color = level_colors.get(level, "")
    reset = Style.RESET_ALL
    
    # Format the log message
    formatted_message = f"{color}[{timestamp}] {level:8} {logger_name}: {message}{reset}"
    
    # Add any additional fields
    extra_fields = {k: v for k, v in event_dict.items() 
                   if k not in ["level", "timestamp", "logger", "event"]}
    
    if extra_fields:
        extra_str = " ".join([f"{k}={v}" for k, v in extra_fields.items()])
        formatted_message += f" | {extra_str}"
    
    return formatted_message


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)
