import streamlit as st
import time
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from enum import Enum

try:
    from service_clients.analytics_client import AnalyticsClient
except ImportError:
    # Fallback for when analytics client is not available
    class AnalyticsClient:
        @staticmethod
        def log_event(event_type: str, **kwargs):
            print(f"Analytics event: {event_type}, {kwargs}")

class ToastType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"

@dataclass
class Toast:
    message: str
    toast_type: ToastType
    duration: int = 3000  # milliseconds
    timestamp: float = None
    id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.id is None:
            self.id = f"toast_{int(self.timestamp * 1000)}_{hash(self.message) % 10000}"

class ToastManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToastManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the toast manager with session state"""
        if 'toast_queue' not in st.session_state:
            st.session_state.toast_queue = []
        if 'active_toasts' not in st.session_state:
            st.session_state.active_toasts = {}
        
        self.analytics_client = AnalyticsClient()
    
    def show_toast(self, message: str, 
                  toast_type: ToastType = ToastType.INFO, 
                  duration: int = 3000) -> None:
        """
        Add a toast notification to the queue
        
        Args:
            message: The message to display
            toast_type: Type of toast (SUCCESS, ERROR, INFO, WARNING)
            duration: Duration in milliseconds to show the toast
        """
        toast = Toast(message=message, toast_type=toast_type, duration=duration)
        
        # Add to queue
        st.session_state.toast_queue.append(toast)
        
        # Log analytics event
        try:
            self.analytics_client.log_event(
                event_type="toast_shown",
                toast_type=toast_type.value,
                message=message[:100],  # Truncate long messages
                duration=duration
            )
        except Exception as e:
            print(f"Failed to log toast analytics: {e}")
    
    def _process_queue(self) -> None:
        """Process the toast queue and move ready toasts to active state"""
        current_time = time.time()
        
        # Move toasts from queue to active if they should be shown
        for toast in list(st.session_state.toast_queue):
            # Check if this toast should be shown now
            if toast.timestamp <= current_time:
                st.session_state.toast_queue.remove(toast)
                st.session_state.active_toasts[toast.id] = toast
    
    def _cleanup_expired_toasts(self) -> None:
        """Remove toasts that have expired"""
        current_time = time.time()
        
        for toast_id in list(st.session_state.active_toasts.keys()):
            toast = st.session_state.active_toasts[toast_id]
            # Check if toast has expired (duration in seconds)
            if current_time - toast.timestamp > (toast.duration / 1000):
                del st.session_state.active_toasts[toast_id]
    
    def render_toasts(self) -> None:
        """Render all active toasts"""
        self._process_queue()
        self._cleanup_expired_toasts()
        
        if not st.session_state.active_toasts:
            return
        
        # Import CSS
        st.markdown("""
        <link rel="stylesheet" type="text/css" href="media_assets/styles/toast.css">
        """, unsafe_allow_html=True)
        
        # Create container for toasts
        toast_container = st.container()
        
        with toast_container:
            # Render each active toast
            for toast_id, toast in st.session_state.active_toasts.items():
                self._render_single_toast(toast)
    
    def _render_single_toast(self, toast: Toast) -> None:
        """Render a single toast notification"""
        # Map toast types to CSS classes
        type_classes = {
            ToastType.SUCCESS: "toast-success",
            ToastType.ERROR: "toast-error",
            ToastType.INFO: "toast-info",
            ToastType.WARNING: "toast-warning"
        }
        
        css_class = type_classes.get(toast.toast_type, "toast-info")
        
        # Calculate remaining time for animation
        elapsed = time.time() - toast.timestamp
        remaining = max(0, (toast.duration / 1000) - elapsed)
        
        st.markdown(f"""
        <div class="toast {css_class}" id="{toast.id}" 
             style="animation-duration: {remaining}s;">
            <div class="toast-content">
                <span class="toast-message">{toast.message}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Convenience functions
def show_success_toast(message: str, duration: int = 3000) -> None:
    """Show a success toast notification"""
    ToastManager().show_toast(message, ToastType.SUCCESS, duration)

def show_error_toast(message: str, duration: int = 5000) -> None:
    """Show an error toast notification"""
    ToastManager().show_toast(message, ToastType.ERROR, duration)

def show_info_toast(message: str, duration: int = 3000) -> None:
    """Show an info toast notification"""
    ToastManager().show_toast(message, ToastType.INFO, duration)

def show_warning_toast(message: str, duration: int = 4000) -> None:
    """Show a warning toast notification"""
    ToastManager().show_toast(message, ToastType.WARNING, duration)
