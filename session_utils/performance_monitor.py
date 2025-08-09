# session_utils/performance_monitor.py
"""
Performance monitoring utilities for MoviePulse application.
Provides function timing and performance logging capabilities.
"""

import time
from datetime import datetime
import logging
from functools import wraps
from typing import Callable, Any, Optional, Dict
import streamlit as st

# Set up logging
logger = logging.getLogger(__name__)

def log_performance(
    operation_name: str,
    start_time: float,
    extra_metadata: Optional[Dict[str, Any]] = None,
    log_level: str = "info"
) -> None:
    """
    Log performance metrics for an operation with contextual metadata.
    
    Args:
        operation_name: Name of the operation being measured
        start_time: Time when operation started (from time.perf_counter())
        extra_metadata: Additional context about the operation
        log_level: Logging level ('info', 'debug', 'warning')
    """
    duration = round(time.perf_counter() - start_time, 4)
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation_name,
        "duration_sec": duration,
        "session_id": st.session_state.get("session_id", "unknown"),
        "metadata": extra_metadata or {}
    }
    
    log_message = f"PERF: {operation_name} took {duration}s"
    
    if log_level == "debug":
        logger.debug(log_message, extra={"perf_data": log_data})
    elif log_level == "warning":
        logger.warning(log_message, extra={"perf_data": log_data})
    else:
        logger.info(log_message, extra={"perf_data": log_data})

def time_it(
    func: Optional[Callable] = None,
    *,
    operation_name: Optional[str] = None,
    log_level: str = "info"
) -> Callable:
    """
    Decorator to measure and log execution time of functions.
    
    Can be used with or without parameters:
    @time_it
    @time_it(operation_name="custom_name")
    @time_it(log_level="debug")
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                name = operation_name or f.__name__
                log_performance(
                    operation_name=name,
                    start_time=start_time,
                    extra_metadata={
                        "module": f.__module__,
                        "function": f.__qualname__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    },
                    log_level=log_level
                )
        return wrapper
    
    # Handle both @time_it and @time_it() cases
    if func is None:
        return decorator
    return decorator(func)

class PerformanceTracker:
    """
    Context manager for tracking performance of code blocks.
    Usage:
        with PerformanceTracker("database_query"):
            # Your code here
    """
    def __init__(
        self,
        operation_name: str,
        log_level: str = "info",
        extra_metadata: Optional[Dict[str, Any]] = None
    ):
        self.operation_name = operation_name
        self.log_level = log_level
        self.extra_metadata = extra_metadata or {}
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log_performance(
            operation_name=self.operation_name,
            start_time=self.start_time,
            extra_metadata=self.extra_metadata,
            log_level=self.log_level
        )
        return False

# Shortcut for common case
perf_track = PerformanceTracker