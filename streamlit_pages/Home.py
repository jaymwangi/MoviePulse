
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

import sys
import os



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
    """Centralized search with URL persistence and test-friendly attributes"""
    with st.container():
        # Main container with explicit test ID
        st.markdown('<div data-testid="search-bar-container"></div>', unsafe_allow_html=True)
        
        search_col, clear_col = st.columns([0.7, 0.3])
        
        with search_col:
            # Modified text input with proper test attributes
            search_input = st.text_input(
                "🔍 Search movies, actors, or moods...",
                key="global_search_query",
                help="Try 'mind-bending sci-fi' or 'Scorsese films'",
                label_visibility="collapsed",
                on_change=lambda: st.query_params.update(q=st.session_state.global_search_query),
                placeholder="Search movies, actors, or moods..."
            )
            
            # Add test attributes via HTML injection
            st.markdown(
                f"""
                <script>
                    document.querySelector('input[aria-label="🔍 Search movies, actors, or moods..."]')
                        .setAttribute('data-testid', 'movie-search-input');
                    document.querySelector('input[aria-label="🔍 Search movies, actors, or moods..."]')
                        .setAttribute('aria-label', 'Search movies input');
                </script>
                """,
                unsafe_allow_html=True
            )

def render_search_results():
    """API-integrated results with test-friendly markup"""
    if not st.session_state.get("global_search_query"):
        return
    
    with st.spinner(f"Searching for '{st.session_state.global_search_query}'..."):
        try:
            # Add results container with test ID
            with st.container():
                st.markdown('<div data-testid="search-results-container"></div>', unsafe_allow_html=True)
                
                time.sleep(0.8)  # Simulate API delay
                movies = TMDBClient().search_movies(st.session_state.global_search_query)
                
                if not movies:
                    st.warning("No results found")
                    try:
                        search_empty_path = os.path.join("media_assets", "icons", "search_empty.png")
                        st.image(search_empty_path, width=300)
                    except:
                        st.markdown("""<div style="font-size: 100px; text-align: center;">🔍</div>""", 
                                  unsafe_allow_html=True)
                    return
                    
                # Results header with test ID
                st.subheader(
                    f"Results for: {st.session_state.global_search_query}",
                    divider="red",
                    help="Search results"
                )
                st.markdown('<div data-testid="results-header"></div>', unsafe_allow_html=True)
                
                # Render grid with explicit test attributes
                with st.container():
                    st.markdown('<div data-testid="movie-grid-container"></div>', unsafe_allow_html=True)
                    MovieGridView(movies, columns=4)
                    
                    # Add test attributes to each movie tile
                    st.markdown(
                        """
                        <script>
                            document.querySelectorAll('.movie-tile').forEach((tile, index) => {
                                tile.setAttribute('data-testid', 'movie-tile');
                                tile.setAttribute('data-visible', 'true');
                            });
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
                
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            try:
                api_error_path = os.path.join("media_assets", "icons", "api_error.png")
                st.image(api_error_path, width=200)
            except:
                st.markdown("""<div style="font-size: 100px; text-align: center;">⚠️</div>""", 
                          unsafe_allow_html=True)
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