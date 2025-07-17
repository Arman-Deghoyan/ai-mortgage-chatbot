"""
Structured logging configuration for the AI Mortgage Chatbot.

This module provides a production-ready logging setup using structlog
with proper formatting, context management, and log levels.
"""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    include_timestamp: bool = True,
    include_process_id: bool = True,
    include_thread_id: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'console')
        include_timestamp: Whether to include timestamps in logs
        include_process_id: Whether to include process ID in logs
        include_thread_id: Whether to include thread ID in logs
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
    ]

    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    if include_process_id:
        processors.append(structlog.processors.add_log_level)

    if include_thread_id:
        processors.append(structlog.processors.add_log_level)

    processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
    )

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True, exception_formatter=structlog.dev.exception_formatter
            )
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get a logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """
    Create a logger with function call context.

    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log

    Returns:
        Logger with function call context
    """
    logger = get_logger("function_call")
    return logger.bind(function=func_name, **kwargs)


def log_api_request(
    method: str,
    path: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **kwargs: Any,
) -> structlog.stdlib.BoundLogger:
    """
    Create a logger for API request logging.

    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context

    Returns:
        Logger with API request context
    """
    logger = get_logger("api_request")
    return logger.bind(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_mortgage_calculation(
    user_id: Optional[str] = None,
    calculation_type: Optional[str] = None,
    **kwargs: Any,
) -> structlog.stdlib.BoundLogger:
    """
    Create a logger for mortgage calculation events.

    Args:
        user_id: User identifier
        calculation_type: Type of calculation (DTI, LTV, etc.)
        **kwargs: Additional calculation context

    Returns:
        Logger with mortgage calculation context
    """
    logger = get_logger("mortgage_calculation")
    return logger.bind(
        user_id=user_id,
        calculation_type=calculation_type,
        **kwargs,
    )


def log_llm_interaction(
    model: Optional[str] = None,
    tokens_used: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    **kwargs: Any,
) -> structlog.stdlib.BoundLogger:
    """
    Create a logger for LLM interaction events.

    Args:
        model: LLM model name
        tokens_used: Number of tokens used
        response_time_ms: Response time in milliseconds
        **kwargs: Additional LLM context

    Returns:
        Logger with LLM interaction context
    """
    logger = get_logger("llm_interaction")
    return logger.bind(
        model=model,
        tokens_used=tokens_used,
        response_time_ms=response_time_ms,
        **kwargs,
    )


# Initialize logging with default configuration
configure_logging()
