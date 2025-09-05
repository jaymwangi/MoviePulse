# -*- coding: utf-8 -*-
"""
Mood Calendar Page - Plan cinematic moods in advance
Integrates with existing theme system and session management
Updated for new CalendarGrid interface and correct SidebarFilters usage
"""
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import datetime
from ui_components.CalendarGrid import CalendarGrid
from ui_components import HeaderBar
from ui_components.SidebarFilters import render_sidebar_filters  # ✅ Correct import
from session_utils import (
    user_profile,
    performance_monitor,
    state_tracker
)
from media_assets.styles.main import initialize_theme

# Utility to safely init session state keys
def init_session_defaults(defaults: dict):
    """Initialize Streamlit session state keys if not already set."""
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Load calendar-specific CSS
def load_calendar_css():
    """Load the calendar-specific CSS styles"""
    try:
        css_file = Path(__file__).parent.parent / "media_assets" / "styles" / "calendar.css"
        if css_file.exists():
            with open(css_file, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            st.warning("Calendar CSS file not found. Using default styles.")
    except Exception as e:
        st.error(f"Error loading calendar CSS: {e}")

# Initialize page with your standard config
def init_page():
    st.set_page_config(
        page_title="Mood Calendar | MoviePulse",
        page_icon="📅",
        layout="wide"
    )
    initialize_theme()
    load_calendar_css()  # Load calendar-specific styles
    HeaderBar.render_app_header()

@performance_monitor.log_load_time
def main():
    init_page()
    
    # Session state initialization
    init_session_defaults({
        'selected_moods': {}
    })
    
    # Use CSS classes for styling
    st.markdown(
        """
        <div class="calendar-container">
            <div class="calendar-header">
                <h1 class="calendar-title">📅 Mood Calendar</h1>
                <p style='color: var(--secondary-text); margin-bottom: 2rem;'>
                    Track your emotional journey through cinema and plan your viewing moods
                </p>
            </div>
        """,
        unsafe_allow_html=True
    )
    
    # Container matching your UI spacing
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Instantiate CalendarGrid - no need to pass month parameter
            # The new CalendarGrid handles navigation internally
            calendar = CalendarGrid(theme=st.session_state.get('theme', 'dark'))
            calendar.render(show_insights=True)
            
        with col2:
            # Use the correct function name from SidebarFilters
            render_sidebar_filters()  # ✅ Fixed function name
            
            # Mood statistics section with CSS classes
            st.markdown("---")
            st.markdown('<div class="insights-container">', unsafe_allow_html=True)
            st.markdown('<h3 class="insights-title">Mood Statistics</h3>', unsafe_allow_html=True)
            
            # Add some quick stats (you can enhance this with real data)
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("Most Common Mood", "😊 Happy", "12 days")
            with col_stat2:
                st.metric("Current Streak", "3 days", "Relaxed")
            
            # Export section
            st.markdown("---")
            st.subheader("Export & Share")
            
            # Export buttons with CSS classes
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                if st.button("📤 Export ICS", use_container_width=True, help="Export to calendar apps"):
                    with st.spinner("Generating calendar file..."):
                        user_profile.export_calendar(format_type="ics")
            
            with export_col2:
                if st.button("📊 Export CSV", use_container_width=True, help="Export as spreadsheet"):
                    with st.spinner("Generating CSV file..."):
                        user_profile.export_calendar(format_type="csv")
            
            if st.button("🔄 Reset Calendar", use_container_width=True, type="secondary"):
                st.session_state.selected_moods = {}
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close insights container
    
    # Close the main calendar container
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()