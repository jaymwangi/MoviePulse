import sys
import os
import streamlit as st
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters, get_active_filters
from ui_components.MovieTile import MovieTile
from ui_components.MovieGridView import MovieGridView
from session_utils.state_tracker import init_session_state, get_current_theme
from media_assets.styles import load_custom_css
from session_utils.user_profile import init_profile
from service_clients.tmdb_client import tmdb_client, FallbackStrategy
from streamlit.components.v1 import html

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ----------------------- UTILITY FUNCTIONS -----------------------
def is_tmdb_available():
    """Check if TMDB client is available and functional"""
    return tmdb_client is not None

def show_service_unavailable():
    """Show consistent service unavailable message"""
    cols = st.columns([0.3, 0.4, 0.3])
    with cols[1]:
        st.error("TMDB service currently unavailable")
        st.image("media_assets/icons/api_error.png", width=300)
        if st.button("🔄 Retry Connection", key="retry_connection"):
            st.rerun()

# ----------------------- CACHED FUNCTIONS -----------------------
@st.cache_data(ttl=3600, show_spinner="Loading trending movies...")
def get_cached_trending_movies(time_window="week"):
    """Get trending movies with caching"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    return tmdb_client.get_trending_movies(time_window=time_window)

@st.cache_data(ttl=600, show_spinner="Searching movies...")
def cached_search(query, filters=None, page=1):
    """Cache search results for 10 minutes"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    return tmdb_client.search_movies(
        query=query,
        filters=filters,
        fallback_strategy=st.session_state.search_fallback_strategy,
        page=page
    )

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_cached_genres():
    """Get genre list with caching"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    return tmdb_client.get_genres()

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
    
    # Initialize session state variables
    if 'search_fallback_strategy' not in st.session_state:
        st.session_state.search_fallback_strategy = FallbackStrategy.RELAX_GRADUAL
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    if 'filter_execution_in_progress' not in st.session_state:
        st.session_state.filter_execution_in_progress = False
    if 'global_search_query' not in st.session_state:
        st.session_state.global_search_query = ""

# ----------------------- STARTER PACK HANDLING -----------------------
def check_first_time_user():
    """Check if user needs starter pack selection"""
    from session_utils.watchlist_manager import load_watchlist
    from session_utils.starter_packs import show_starter_pack_selector
    
    user_id = st.session_state.get("user_id", "anonymous")
    watchlist = load_watchlist().get(user_id, {}).get("movies", [])
    
    if not watchlist and not st.session_state.starter_pack_selected:
        show_starter_pack_selector()
        st.stop()  # Prevent rest of app from loading until selection

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
        st.markdown('<div data-testid="search-bar-container"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            search_input = st.text_input(
                "🔍 Search movies, actors, or moods...",
                value=st.session_state.global_search_query,
                key="search_input_field",
                help="Try 'mind-bending sci-fi' or 'Scorsese films'",
                label_visibility="collapsed",
                placeholder="Search movies, actors, or moods...",
                disabled=st.session_state.filter_execution_in_progress or not is_tmdb_available()
            )
            
            # Update search state if input changes
            if search_input != st.session_state.global_search_query:
                st.session_state.global_search_query = search_input
                st.session_state.current_page = 1
                if search_input and search_input not in st.session_state.search_history:
                    st.session_state.search_history.append(search_input)
                st.rerun()
            
            # Add test attributes
            st.markdown(
                """
                <script>
                    document.querySelector('input[aria-label="🔍 Search movies, actors, or moods..."]')
                        .setAttribute('data-testid', 'movie-search-input');
                </script>
                """,
                unsafe_allow_html=True
            )
def render_search_results():
    """API-integrated results with enhanced filter support"""
    if not st.session_state.get("global_search_query"):
        return
    
    if not is_tmdb_available():
        show_service_unavailable()
        return
    
    # Get current filters once at the start
    filters = get_active_filters()
    
    # Show watchlist if active
    if filters.get("watchlist_active"):
        from ui_components import WatchlistView
        WatchlistView.render_watchlist_grid()
        return
    
    # Show loading state for filter-triggered searches
    if st.session_state.filter_execution_in_progress:
        with st.spinner("🔄 Applying filters..."):
            st.session_state.filter_execution_in_progress = False
            st.toast("Filters applied successfully!", icon="✅")
    
    with st.spinner(f"🔍 Searching for '{st.session_state.global_search_query}'..."):
        try:
            # Search with hybrid filtering (using cached version)
            results, total_pages = cached_search(
                query=st.session_state.global_search_query,
                filters=filters,  # Use the filters we already got
                page=st.session_state.current_page
            )
            
            with st.container():
                st.markdown('<div data-testid="search-results-container"></div>', unsafe_allow_html=True)
                
                if not results:
                    cols = st.columns([0.3, 0.4, 0.3])
                    with cols[1]:
                        st.warning("No results found matching your criteria")
                        st.image("media_assets/icons/search_empty.png", width=300)
                        if st.button("Try Relaxing Filters",
                                   disabled=st.session_state.filter_execution_in_progress):
                            st.session_state.search_fallback_strategy = FallbackStrategy.RELAX_ALL
                            st.rerun()
                    return
                
                st.subheader(f"Results for: {st.session_state.global_search_query}", divider="red")
                
                # Pagination controls
                if total_pages > 1:
                    cols = st.columns(3)
                    with cols[1]:
                        page_select = st.selectbox(
                            "Page",
                            range(1, total_pages + 1),
                            index=st.session_state.current_page - 1,
                            key="page_select",
                            disabled=st.session_state.filter_execution_in_progress
                        )
                        if page_select != st.session_state.current_page:
                            st.session_state.current_page = page_select
                            st.rerun()
                
                MovieGridView(results, columns=4)

        except Exception as e:
            cols = st.columns([0.3, 0.4, 0.3])
            with cols[1]:
                st.error(f"Search failed: {str(e)}")
                st.image("media_assets/icons/api_error.png", width=300)
                st.button("🔄 Retry", 
                         key="retry_search",
                         disabled=st.session_state.filter_execution_in_progress)
                
def render_trending_section():
    """Trending movies with improved fallback handling"""
    st.subheader("🔥 Trending This Week", divider="red")
    
    if not is_tmdb_available():
        show_service_unavailable()
        # Show fallback content only if it's not an auth issue
        MovieGridView([
            {"title": "Dune 2", "poster_path": "media_assets/posters/dune2.jpg"},
            {"title": "Oppenheimer", "poster_path": "media_assets/posters/oppenheimer.jpg"},
        ], columns=5)
        return
    
    try:
        trending_movies, _ = get_cached_trending_movies(time_window="week")
        
        if not trending_movies:
            cols = st.columns([0.3, 0.4, 0.3])
            with cols[1]:
                st.warning("No trending movies found")
                st.image("media_assets/icons/no_results.png", width=300)
            return
            
        MovieGridView(trending_movies, columns=5)
        
    except Exception as e:
        cols = st.columns([0.3, 0.4, 0.3])
        with cols[1]:
            st.error(f"Couldn't load trending movies: {str(e)}")
            st.image("media_assets/icons/api_error.png", width=300)
            
        # Only show fallback if it's not an API key issue
        if "401" not in str(e):
            MovieGridView([
                {"title": "Dune 2", "poster_path": "media_assets/posters/dune2.jpg"},
                {"title": "Oppenheimer", "poster_path": "media_assets/posters/oppenheimer.jpg"},
            ], columns=5)

def render_advanced_search_options():
    """Additional search controls in sidebar"""
    with st.expander("🔧 Advanced Search Options"):
        st.radio(
            "When no results found:",
            options=[
                FallbackStrategy.NONE,
                FallbackStrategy.RELAX_GRADUAL, 
                FallbackStrategy.RELAX_ALL
            ],
            index=1,
            key="search_fallback_strategy",
            format_func=lambda x: {
                FallbackStrategy.NONE: "Keep strict filters",
                FallbackStrategy.RELAX_GRADUAL: "Smart relaxation (recommended)",
                FallbackStrategy.RELAX_ALL: "Show any results"
            }[x],
            disabled=st.session_state.filter_execution_in_progress or not is_tmdb_available()
        )
        
        if st.session_state.search_history:
            st.markdown("**Recent Searches**")
            for query in reversed(st.session_state.search_history[-5:]):
                if st.button(query, 
                            use_container_width=True,
                            disabled=st.session_state.filter_execution_in_progress):
                    st.session_state.global_search_query = query
                    st.session_state.current_page = 1
                    st.rerun()

def render_sidebar_filters_with_loading():
    """Wrapper for sidebar filters with loading state"""
    if not is_tmdb_available():
        st.sidebar.warning("Filters unavailable - service disconnected")
        return
    
    # Load genres into cache if not already loaded
    if 'genres' not in st.session_state:
        try:
            st.session_state.genres = get_cached_genres()
        except Exception as e:
            st.sidebar.error("Couldn't load genres")
            return
    
    if st.session_state.filter_execution_in_progress:
        with st.spinner("Applying filters..."):
            render_sidebar_filters()
    else:
        render_sidebar_filters()

    # Set execution state when filters change
    if st.session_state.get('filters_changed'):
        st.session_state.filter_execution_in_progress = True
        st.session_state.filters_changed = False
        st.rerun()


def render_app_footer():
    """Theme-aware footer with service status"""
    status = "✅ Online" if is_tmdb_available() else "❌ Offline"
    st.markdown(f"""
    <div style="text-align: center; margin-top: 4rem; padding: 1rem; opacity: 0.6;">
        <p>© 2024 MoviePulse | Data from TMDB | Service: {status} | v2.4</p>
    </div>
    """, unsafe_allow_html=True)
# ----------------------- MAIN EXECUTION -----------------------
if __name__ == "__main__":
    configure_page()

    from session_utils.user_profile import init_profile
    init_profile()
    
    # Layout structure
    render_app_header()
    
    # Sidebar components
    with st.sidebar:
        render_sidebar_filters_with_loading()
        render_advanced_search_options()
            
    # Main content area
    if not st.session_state.global_search_query:
        render_hero_section()
    
    render_search_bar()
    
    # Conditional content display
    if st.session_state.global_search_query:
        render_search_results()
    else:
        render_trending_section()
    
    render_app_footer()