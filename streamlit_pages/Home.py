# streamlit_pages/1_🏠_Home.py
import streamlit as st
import time
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters
from ui_components.MovieTile import MovieTile
from ui_components.MovieGridView import MovieGridView
from session_utils.state_tracker import init_session_state, get_current_theme
from media_assets.styles import load_custom_css
from service_clients.tmdb_client import TMDBClient
from streamlit.components.v1 import html

# ----------------------- SETUP -----------------------
def configure_page():
    """Initialize page settings with theme awareness"""
    st.set_page_config(
        page_title="MoviePulse - Discover Your Next Favorite Film",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    init_session_state()
    load_custom_css(get_current_theme())
    html("<script src='media_assets/scripts/hover_test.js'></script>")

# ----------------------- MAIN CONTENT SECTIONS -----------------------
def render_hero_section():
    """Dynamic hero section with theme-responsive logo"""
    logo_path = f"media_assets/logos/moviepulse_{get_current_theme()}.png"
    st.markdown(f"""
    <div class="hero-section" style="text-align: center; margin-bottom: 2rem;">
        <img src="{logo_path}" width="650" style="margin-bottom: 0.5rem;">
        <p style="font-size: 1.2rem; opacity: 0.8; margin-top: 0;">
            Your <span style="color: #FF4B4B;">cinematic universe</span>—curated, intelligent, immersive
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_search_bar():
    """Centralized search with URL persistence"""
    with st.container():
        search_col, clear_col = st.columns([0.7, 0.3])
        
        # Sync with URL params
        if "q" in st.query_params:
            st.session_state.global_search_query = st.query_params["q"]
        
        with search_col:
            st.text_input(
                "🔍 Search movies, actors, or moods...",
                key="global_search_query",
                help="Try 'mind-bending sci-fi' or 'Scorsese films'",
                label_visibility="collapsed",
                on_change=lambda: st.query_params.update(q=st.session_state.global_search_query)
            )
        
        with clear_col:
            if st.session_state.get("global_search_query"):
                if st.button("❌ Clear", use_container_width=True):
                    st.session_state.global_search_query = ""
                    if "q" in st.query_params:
                        del st.query_params["q"]
                    st.rerun()

def render_search_results():
    """API-integrated results with loading states"""
    if not st.session_state.get("global_search_query"):
        return
    
    with st.spinner(f"Searching for '{st.session_state.global_search_query}'..."):
        try:
            time.sleep(0.8)  # Simulate API delay
            movies = TMDBClient().search_movies(st.session_state.global_search_query)
            
            if not movies:
                st.warning("No results found")
                st.image("media_assets/icons/search_empty.png", width=300)
                return
                
            st.subheader(f"Results for: {st.session_state.global_search_query}")
            MovieGridView(movies, columns=4)
            
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            st.image("media_assets/icons/api_error.png", width=200)
            st.button("🔄 Retry", key="retry_search")

def render_trending_section():
    """Trending movies grid"""
    st.subheader("🔥 Trending This Week", divider="red")
    MovieGridView([
        {"title": "Dune 2", "poster_path": "media_assets/posters/dune2.jpg", "release_year": "2024"},
        {"title": "Oppenheimer", "poster_path": "media_assets/posters/oppenheimer.jpg", "release_year": "2023"},
        # Add 3 more trending movies...
    ], columns=5)

def render_app_footer():
    """Theme-aware footer"""
    st.markdown("""
    <div style="text-align: center; margin-top: 4rem; padding: 1rem; opacity: 0.6;">
        <p>© 2024 MoviePulse | Data from TMDB | v2.1</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------- MAIN EXECUTION -----------------------
if __name__ == "__main__":
    configure_page()
    render_app_header()
    render_sidebar_filters()
    render_hero_section()
    render_search_bar()
    
    if st.session_state.get("global_search_query"):
        render_search_results()
    else:
        render_trending_section()
    
    render_app_footer()