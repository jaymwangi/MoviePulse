"""
Performance monitoring utilities for MoviePulse
Track page load times and component rendering performance
"""

import time
import functools
import streamlit as st
from typing import Callable, Any

def log_load_time(func: Callable) -> Callable:
    """
    Decorator to log execution time of page load functions
    
    Args:
        func: The function to be decorated (typically a page's main function)
        
    Returns:
        The wrapped function with timing instrumentation
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            
            # Log to session state if available
            if 'performance_metrics' not in st.session_state:
                st.session_state.performance_metrics = {}
                
            st.session_state.performance_metrics[func.__name__] = {
                'load_time': elapsed,
                'timestamp': time.time()
            }
            
            # Optional: Log to console for debugging
            print(f"⏱️ {func.__name__} executed in {elapsed:.3f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            print(f"⚠️ {func.__name__} failed after {elapsed:.3f}s - {str(e)}")
            raise
    
    return wrapper

# Create alias for backward compatibility
log_performance = log_load_time

def get_performance_metrics() -> dict:
    """
    Returns collected performance metrics
    
    Returns:
        dict: Dictionary of all recorded performance metrics
    """
    return st.session_state.get('performance_metrics', {})

def clear_metrics() -> None:
    """
    Clears all stored performance metrics
    """
    if 'performance_metrics' in st.session_state:
        del st.session_state['performance_metrics']

# Make decorator available at package level
__all__ = ['log_load_time', 'log_performance', 'get_performance_metrics', 'clear_metrics']