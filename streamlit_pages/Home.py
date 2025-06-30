import sys
import os
import streamlit as st
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters, get_active_filters
from ui_components.MovieTile import MovieTile
from ui_components.MovieGridView import MovieGridView
from session_utils.state_tracker import init_session_state, get_current_theme
from media_assets.styles import load_custom_css
from service_clients.tmdb_client import tmdb_client, FallbackStrategy
from streamlit.components.v1 import html

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
                disabled=st.session_state.filter_execution_in_progress
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
    
    # Show loading state for filter-triggered searches
    if st.session_state.filter_execution_in_progress:
        with st.spinner("🔄 Applying filters..."):
            st.session_state.filter_execution_in_progress = False
            st.toast("Filters applied successfully!", icon="✅")
    
    with st.spinner(f"🔍 Searching for '{st.session_state.global_search_query}'..."):
        try:
            # Get current filters from sidebar
            filters = get_active_filters()
            
            # Add retry button if previous attempt failed
            if st.session_state.get('search_failed'):
                if st.button("🔄 Retry Search", 
                           key="retry_search",
                           disabled=st.session_state.filter_execution_in_progress):
                    st.session_state.search_failed = False
                    st.rerun()
                return
            
            # Search with hybrid filtering
            results, total_pages = tmdb_client.search_movies(
                query=st.session_state.global_search_query,
                filters=filters,
                fallback_strategy=st.session_state.search_fallback_strategy,
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
                
                # Show filter relaxation warning if applicable
                if st.session_state.get('filters_were_relaxed'):
                    st.toast("Showing results with relaxed filters", icon="ℹ️")
                    st.session_state.filters_were_relaxed = False
                
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
            st.session_state.search_failed = True
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
    
    # Show loading state for filter-triggered searches
    if st.session_state.filter_execution_in_progress:
        with st.spinner("🔄 Applying filters..."):
            st.session_state.filter_execution_in_progress = False
            st.toast("Filters applied successfully!", icon="✅")
    
    try:
        filters = get_active_filters()
        
        trending_movies = tmdb_client.get_trending_movies(
            time_window="week",
            filters=filters,
            fallback_strategy=FallbackStrategy.RELAX_GRADUAL
        )
        
        if not trending_movies:
            cols = st.columns([0.3, 0.4, 0.3])
            with cols[1]:
                st.warning("No trending movies match your filters")
                st.image("media_assets/icons/no_results.png", width=300)
                if st.button("Show Popular Movies Anyway",
                           disabled=st.session_state.filter_execution_in_progress):
                    st.session_state.search_fallback_strategy = FallbackStrategy.RELAX_ALL
                    st.rerun()
            return
            
        # Show filter relaxation notice if applicable
        if st.session_state.get('trending_filters_relaxed'):
            st.toast("Showing trending movies with relaxed filters", icon="ℹ️")
            st.session_state.trending_filters_relaxed = False
            
        MovieGridView(trending_movies, columns=5)
        
    except Exception as e:
        cols = st.columns([0.3, 0.4, 0.3])
        with cols[1]:
            st.error(f"Couldn't load trending movies: {str(e)}")
            st.image("media_assets/icons/api_error.png", width=300)
            if st.button("Try Loading Again",
                       disabled=st.session_state.filter_execution_in_progress):
                st.rerun()
        
        # Fallback to static content
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
            disabled=st.session_state.filter_execution_in_progress
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
    """Theme-aware footer"""
    st.markdown("""
    <div style="text-align: center; margin-top: 4rem; padding: 1rem; opacity: 0.6;">
        <p>© 2024 MoviePulse | Data from TMDB | v2.3</p>
    </div>
    """, unsafe_allow_html=True)


# ----------------------- MAIN EXECUTION -----------------------
if __name__ == "__main__":
    configure_page()
    
    # Layout structure
    render_app_header()  # Now contains only branding/theme toggle
    
    # Sidebar components
    with st.sidebar:
        render_sidebar_filters_with_loading()
        render_advanced_search_options()
    
    # Main content area
    if not st.session_state.global_search_query:
        render_hero_section()  # Only show hero when no search active
    
    render_search_bar()  # Single search bar in main content
    
    # Conditional content display
    if st.session_state.global_search_query:
        render_search_results()
    else:
        render_trending_section()
    
    render_app_footer()