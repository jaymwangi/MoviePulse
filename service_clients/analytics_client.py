import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import streamlit as st

class AnalyticsClient:
    """
    Singleton client for logging analytics events to a JSONL file.
    Captures user interactions and system events for diagnostics.
    """
    _instance = None
    _initialized = False
    MAX_FILE_SIZE_MB = 10  # Rotate file after 10MB
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AnalyticsClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.analytics_file = "static_data/analytics_events.jsonl"
            self._ensure_directory_exists()
            self._initialized = True
    
    def _ensure_directory_exists(self):
        """Create the directory for analytics data if it doesn't exist."""
        os.makedirs(os.path.dirname(self.analytics_file), exist_ok=True)
    
    def _validate_event(self, event: Dict[str, Any]) -> bool:
        required_fields = {"timestamp", "event_type"}
        return all(field in event for field in required_fields)
    
    def _check_file_size(self):
        if os.path.exists(self.analytics_file):
            size_mb = os.path.getsize(self.analytics_file) / (1024 * 1024)
            if size_mb > self.MAX_FILE_SIZE_MB:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_file = f"static_data/analytics_events_{timestamp}.jsonl"
                os.rename(self.analytics_file, rotated_file)
                print(f"Rotated analytics file to: {rotated_file}")
    
    def _get_session_id(self) -> Optional[str]:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()
            if ctx and hasattr(ctx, "session_id"):
                return ctx.session_id
        except:
            pass
        return None
    
    def _create_base_event(self, event_type: str, **kwargs) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "session_id": self._get_session_id(),
            **kwargs
        }
    
    def log_event(self, event_type: str, **kwargs) -> bool:
        try:
            self._check_file_size()
            event = self._create_base_event(event_type, **kwargs)
            if not self._validate_event(event):
                print("Invalid event structure")
                return False
            with open(self.analytics_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            return True
        except Exception as e:
            print(f"Failed to log analytics event: {e}")
            return False
    
    def log_events(self, events: List[Dict[str, Any]]) -> bool:
        try:
            self._check_file_size()
            valid_events = [e for e in events if self._validate_event(e)]
            with open(self.analytics_file, "a") as f:
                for event in valid_events:
                    f.write(json.dumps(event) + "\n")
            return True
        except Exception as e:
            print(f"Failed to batch log events: {e}")
            return False

analytics_client = AnalyticsClient()

if __name__ == "__main__":
    analytics_client.log_event("test_event", message="Testing analytics client")
    analytics_client.log_event("navigation", from_page="home", to_page="details", movie_id=123)
    events = [
        analytics_client._create_base_event("watchlist_update", action="add", movie_id=456, title="Test Movie 1"),
        analytics_client._create_base_event("watchlist_update", action="add", movie_id=789, title="Test Movie 2"),
        analytics_client._create_base_event("toast_notification", message="Movies added successfully", type="success")
    ]
    analytics_client.log_events(events)
    print("Test events logged successfully!")
