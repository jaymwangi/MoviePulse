# ui_components/SidebarFilters.py
import streamlit as st
from session_utils.state_tracker import get_current_theme
from typing import Dict, List
import json

def load_genres() -> List[Dict[str, str]]:
    """Load genre data from static file with error handling"""
    try:
        with open("static_data/genres.json", "r") as f:
            return json.load(f).get("genres", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"}
        ]  # Fallback basic genres

def render_sidebar_filters():
    """
    Creates the collapsible filter sidebar with:
    - Genre multi-select
    - Year range slider
    - Rating filter
    - Mood tags (future feature)
    - Reset button
    """
    with st.sidebar:
        # ---- 1. SIDEBAR HEADER ----
        st.markdown(f"""
        <style>
            .sidebar-header {{
                color: {'#FAFAFA' if get_current_theme() == 'dark' else '#0E1117'};
                font-size: 1.3rem;
                margin-bottom: 1rem;
            }}
            .st-emotion-cache-1oe5cao {{
                padding-top: 2rem;
            }}
        </style>
        <div class="sidebar-header">🎬 Filter Movies</div>
        """, unsafe_allow_html=True)
        
        # ---- 2. GENRE SELECTOR ----
        with st.expander("**🎭 Genres**", expanded=True):
            all_genres = load_genres()
            selected_genres = st.multiselect(
                "Select genres",
                options=[g["name"] for g in all_genres],
                default=st.session_state.get("selected_genres", []),
                key="genre_selector",
                label_visibility="collapsed"
            )
            st.session_state.selected_genres = selected_genres
        
        # ---- 3. YEAR RANGE ----
        with st.expander("**📅 Release Year**", expanded=True):
            year_range = st.slider(
                "Select year range",
                min_value=1950,
                max_value=2025,
                value=(st.session_state.get("year_range", (2000, 2024))),
                key="year_slider",
                step=1
            )
            st.session_state.year_range = year_range
        
        # ---- 4. RATING FILTER ----
        with st.expander("**⭐ Rating**", expanded=True):
            min_rating = st.slider(
                "Minimum rating",
                min_value=0.0,
                max_value=10.0,
                value=st.session_state.get("min_rating", 7.0),
                step=0.5,
                key="rating_slider"
            )
            st.session_state.min_rating = min_rating
        
        # ---- 5. RESET BUTTON ----
        st.divider()
        if st.button("♻️ Reset All Filters", use_container_width=True):
            reset_filters()
        
        # ---- 6. FUTURE MOOD TAGS PLACEHOLDER ----
        st.markdown("""
        <div style="margin-top: 2rem; opacity: 0.7; font-size: 0.8rem;">
            <i>Mood filters coming soon!</i>
        </div>
        """, unsafe_allow_html=True)

def reset_filters():
    """Clear all filter selections"""
    st.session_state.selected_genres = []
    st.session_state.year_range = (2000, 2024)
    st.session_state.min_rating = 7.0
    st.toast("Filters reset!", icon="🔄")