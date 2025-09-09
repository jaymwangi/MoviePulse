# pages/page_10_diagnostics.py
import streamlit as st
import pandas as pd
from datetime import datetime
from service_clients.diagnostics_logger import DiagnosticsLogger

def main():
    st.set_page_config(
        page_title="MoviePulse - Diagnostics",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 System Diagnostics")
    st.markdown("Monitor system health, analytics events, and session metrics.")
    
    # Read analytics events
    events = DiagnosticsLogger.read_analytics_events()
    
    # Get session metrics
    metrics = DiagnosticsLogger.get_session_metrics()
    
    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Analytics Events")
        
        if not events:
            st.info("No analytics events recorded yet.")
        else:
            # Show event count by type
            event_types = {}
            for event in events:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            st.subheader("Event Summary")
            event_summary_df = pd.DataFrame({
                'Event Type': list(event_types.keys()),
                'Count': list(event_types.values())
            })
            st.dataframe(event_summary_df, use_container_width=True)
            
            # Show detailed events in expandable sections
            st.subheader("Event Details")
            
            # Navigation events
            nav_events = DiagnosticsLogger.get_navigation_events(events)
            with st.expander(f"Navigation Events ({len(nav_events)})"):
                if nav_events:
                    nav_df = pd.DataFrame(nav_events)
                    st.dataframe(nav_df, use_container_width=True)
                else:
                    st.info("No navigation events recorded.")
            
            # Toast events
            toast_events = DiagnosticsLogger.get_toast_events(events)
            with st.expander(f"Toast Events ({len(toast_events)})"):
                if toast_events:
                    toast_df = pd.DataFrame(toast_events)
                    st.dataframe(toast_df, use_container_width=True)
                else:
                    st.info("No toast events recorded.")
            
            # All events
            with st.expander(f"All Events ({len(events)})"):
                events_df = pd.DataFrame(events)
                st.dataframe(events_df, use_container_width=True)
    
    with col2:
        st.header("System Metrics")
        
        # TMDB Cache
        st.metric(
            label="TMDB Cache Size",
            value=metrics['tmdb_cache_size'],
            help="Number of items cached from TMDB API"
        )
        
        # Watchlist Count
        st.metric(
            label="Watchlist Count",
            value=metrics['watchlist_count'],
            help="Number of movies in the current watchlist"
        )
        
        # Session Info
        st.subheader("Session Information")
        session_info = metrics['active_session']
        st.text(f"Session ID: {session_info['session_id']}")
        st.text(f"Session Start: {session_info['session_start_time']}")
        
        # User Preferences
        st.subheader("User Preferences")
        if session_info['user_preferences']:
            for key, value in session_info['user_preferences'].items():
                st.text(f"{key}: {value}")
        else:
            st.info("No user preferences set.")
        
        # System Info
        st.subheader("System Information")
        st.text(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.text(f"Streamlit Version: {st.__version__}")
        
        # Refresh button
        if st.button("🔄 Refresh Diagnostics", use_container_width=True):
            st.rerun()

if __name__ == "__main__":
    main()