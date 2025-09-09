import json
import os
from datetime import datetime
from typing import List, Dict, Any
import streamlit as st

class DiagnosticsLogger:
    """Service to read and analyze analytics events for diagnostics"""
    
    @staticmethod
    def read_analytics_events() -> List[Dict[str, Any]]:
        """Read analytics events from JSONL file"""
        events = []
        analytics_file = "static_data/analytics_events.jsonl"
        
        if not os.path.exists(analytics_file):
            return events
            
        try:
            with open(analytics_file, 'r') as file:
                for line in file:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            st.error(f"Error reading analytics file: {e}")
            
        return events
    
    @staticmethod
    def filter_events_by_type(events: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
        """Filter events by type"""
        return [event for event in events if event.get('event_type') == event_type]
    
    @staticmethod
    def get_navigation_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get navigation events"""
        return DiagnosticsLogger.filter_events_by_type(events, 'navigation')
    
    @staticmethod
    def get_toast_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get toast events"""
        return DiagnosticsLogger.filter_events_by_type(events, 'toast')
    
    @staticmethod
    def get_session_metrics() -> Dict[str, Any]:
        """Get session metrics"""
        session_state = st.session_state
        
        # Get TMDB cache size
        tmdb_cache_size = 0
        if hasattr(session_state, 'tmdb_cache'):
            tmdb_cache_size = len(session_state.tmdb_cache)
        
        # Get watchlist count
        watchlist_count = 0
        if hasattr(session_state, 'watchlist'):
            watchlist_count = len(session_state.watchlist)
        
        # Get active session info
        active_session = {
            'session_id': session_state.get('session_id', 'N/A'),
            'session_start_time': session_state.get('session_start_time', 'N/A'),
            'user_preferences': session_state.get('user_preferences', {})
        }
        
        return {
            'tmdb_cache_size': tmdb_cache_size,
            'watchlist_count': watchlist_count,
            'active_session': active_session
        }
