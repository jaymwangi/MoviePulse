import sys
import os
import streamlit as st
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters, get_active_filters
from ui_components.MovieTile import MovieTile
from ui_components.MovieGridView import MovieGridView
from session_utils.state_tracker import init_session_state, get_current_theme
from media_assets.styles import load_custom_css
from session_utils.user_profile import (
    init_profile, initialize_preferences_session, 
    get_theme, set_theme, get_font, set_font,
    is_spoiler_free, set_spoiler_free, is_dyslexia_mode, set_dyslexia_mode,
    get_critic_mode_pref, set_critic_mode_pref,
    migrate_old_preferences
)
from service_clients.tmdb_client import tmdb_client, FallbackStrategy
from streamlit.components.v1 import html
import logging
logger = logging.getLogger(__name__)


# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import theme applier from utils
try:
    from utils.theme_applier import apply_theme_settings, inject_custom_css
    THEME_APPLIER_AVAILABLE = True
except ImportError:
    # Fallback if theme applier isn't available yet
    THEME_APPLIER_AVAILABLE = False
    apply_theme_settings = lambda: None
    inject_custom_css = lambda: None

# Import settings handler for sidebar integration
try:
    from utils.settings_handler import handle_settings_change
    SETTINGS_HANDLER_AVAILABLE = True
except ImportError:
    SETTINGS_HANDLER_AVAILABLE = False

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

# Critic mode labels for display
CRITIC_MODE_LABELS = {
    "balanced": "🎭 Balanced Critic",
    "arthouse": "🎨 Arthouse Critic", 
    "blockbuster": "🎬 Blockbuster Critic",
    "indie": "🌟 Indie Critic"
}

# ----------------------- CACHED FUNCTIONS -----------------------
@st.cache_data(ttl=3600, show_spinner="Loading trending movies...")
def get_cached_trending_movies(time_window="week"):
    """Get trending movies with caching and critic mode"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    
    try:
        # Get current critic mode preference
        critic_mode = get_critic_mode_pref()
        
        # Call the optimized TMDB client with critic_mode parameter
        return tmdb_client.get_trending_movies(
            time_window=time_window,
            critic_mode=critic_mode
        )
    except Exception as e:
        logger.error(f"Failed to get trending movies with critic mode: {str(e)}")
        # Fallback to basic trending movies without critic mode
        return tmdb_client.get_trending_movies(time_window=time_window)

@st.cache_data(ttl=600, show_spinner="Searching movies...")
def cached_search(query, filters=None, page=1):
    """Cache search results for 10 minutes with critic mode"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    
    try:
        # Get current critic mode preference
        critic_mode = get_critic_mode_pref()
        
        # Call the optimized TMDB client with critic_mode parameter
        return tmdb_client.search_movies(
            query=query,
            filters=filters,
            fallback_strategy=st.session_state.search_fallback_strategy,
            page=page,
            critic_mode=critic_mode
        )
    except Exception as e:
        logger.error(f"Failed to search with critic mode: {str(e)}")
        # Fallback to basic search without critic mode
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

@st.cache_data(ttl=3600)
def get_cached_actor_details(actor_id):
    """Get actor details with caching"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    return tmdb_client.get_actor_details(actor_id)

@st.cache_data(ttl=3600)
def get_cached_director_filmography(director_id):
    """Get director filmography with caching"""
    if not is_tmdb_available():
        raise RuntimeError("TMDB client not available")
    return tmdb_client.get_director_filmography(director_id)

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
    
    # Initialize user preferences and migrate old data
    migrate_old_preferences()
    initialize_preferences_session()
    
    # Apply theme settings before loading CSS
    apply_theme_settings_wrapper()
    
    # Load custom CSS (fallback if theme applier not available)
    if not THEME_APPLIER_AVAILABLE:
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
    
    # Clear stale actor/director session states on app load
    for key in ['current_actor', 'current_director']:
        if key in st.session_state:
            del st.session_state[key]

def apply_theme_settings_wrapper():
    """Wrapper to apply theme settings with fallback handling"""
    if THEME_APPLIER_AVAILABLE:
        try:
            apply_theme_settings()
            inject_custom_css()
        except Exception as e:
            st.error(f"Theme application failed: {str(e)}")
            # Fallback to basic theme application
            apply_user_preferences_fallback()
    else:
        apply_user_preferences_fallback()

def apply_user_preferences_fallback():
    """Fallback theme application if theme applier is not available"""
    current_theme = get_theme()
    if 'current_theme' not in st.session_state or st.session_state.current_theme != current_theme:
        st.session_state.current_theme = current_theme
        load_custom_css(current_theme)
    
    # Apply accessibility settings
    apply_accessibility_settings()

def apply_accessibility_settings():
    """Apply accessibility settings based on user preferences"""
    if is_dyslexia_mode():
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=OpenDyslexic&display=swap');
        * {
            font-family: 'OpenDyslexic', sans-serif !important;
            letter-spacing: 0.05em;
            line-height: 1.8;
            word-spacing: 0.1em;
        }
        </style>
        """, unsafe_allow_html=True)
    
    font_pref = get_font()
    if font_pref == "large":
        st.markdown("""
        <style>
        .stApp * {
            font-size: 18px !important;
        }
        h1 { font-size: 2.5rem !important; }
        h2 { font-size: 2rem !important; }
        h3 { font-size: 1.75rem !important; }
        p, div { font-size: 18px !important; }
        </style>
        """, unsafe_allow_html=True)
    elif font_pref == "dyslexia":
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=OpenDyslexic&display=swap');
        * {
            font-family: 'OpenDyslexic', sans-serif !important;
        }
        </style>
        """, unsafe_allow_html=True)

# ----------------------- STARTER PACK HANDLING -----------------------
def check_first_time_user():
    """Simplified first-time user check without starter pack selection"""
    from session_utils.watchlist_manager import load_watchlist
    
    user_id = st.session_state.get("user_id", "anonymous")
    watchlist = load_watchlist().get(user_id, {}).get("movies", [])
    
    if not watchlist:
        st.session_state.starter_pack_selected = True  # Skip starter pack selection

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
    """API-integrated results with enhanced filter support and critic mode"""
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
    
    # Get current critic mode for display
    critic_mode = get_critic_mode_pref()
    
    with st.spinner(f"🔍 Searching for '{st.session_state.global_search_query}'..."):
        try:
            # Search with hybrid filtering (using cached version)
            results, total_pages = cached_search(
                query=st.session_state.global_search_query,
                filters=filters,
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
                
                # Display results with critic mode info
                st.subheader(f"Results for: {st.session_state.global_search_query}", divider="red")
                st.caption(f"🎯 Viewing through: {CRITIC_MODE_LABELS.get(critic_mode, 'Balanced Critic')}")
                
                # Apply spoiler-free mode if enabled
                if is_spoiler_free():
                    st.info("🔒 Spoiler-free mode enabled - sensitive content hidden")
                
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
                
                MovieGridView.render(results, columns=4)

        except Exception as e:
            cols = st.columns([0.3, 0.4, 0.3])
            with cols[1]:
                st.error(f"Search failed: {str(e)}")
                st.image("media_assets/icons/api_error.png", width=300)
                st.button("🔄 Retry", 
                         key="retry_search",
                         disabled=st.session_state.filter_execution_in_progress)

def render_trending_section():
    """Trending movies with critic mode filtering"""
    # Get current critic mode for display
    critic_mode = get_critic_mode_pref()
    
    st.subheader(f"🔥 Trending This Week • {CRITIC_MODE_LABELS.get(critic_mode, '')}", divider="red")
    st.caption(f"🎯 Viewing through: {CRITIC_MODE_LABELS.get(critic_mode, 'Balanced Critic')}")
    
    if not is_tmdb_available():
        show_service_unavailable()
        # Show fallback content only if it's not an auth issue
        MovieGridView.render([
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
            
        MovieGridView.render(trending_movies, columns=5)
        
    except Exception as e:
        cols = st.columns([0.3, 0.4, 0.3])
        with cols[1]:
            st.error(f"Couldn't load trending movies: {str(e)}")
            st.image("media_assets/icons/api_error.png", width=300)
            
        # Only show fallback if it's not an API key issue
        if "401" not in str(e):
            MovieGridView.render([
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

def render_quick_settings_sidebar():
    """Render quick settings in sidebar with critic mode"""
    st.sidebar.divider()
    st.sidebar.header("⚙️ Quick Settings")
    
    # Theme selection
    current_theme = get_theme()
    new_theme = st.sidebar.selectbox(
        "Theme",
        options=["dark", "light", "system"],
        index=["dark", "light", "system"].index(current_theme),
        key="sidebar_theme_select",
        label_visibility="collapsed"
    )
    
    if new_theme != current_theme:
        if SETTINGS_HANDLER_AVAILABLE:
            handle_settings_change("theme", new_theme)
        else:
            set_theme(new_theme)
            st.rerun()
    
    # Critic mode selection - handle 'default' value gracefully
    current_critic_mode = get_critic_mode_pref()
    
    # Define valid critic modes and handle invalid/old values
    valid_critic_modes = ["balanced", "arthouse", "blockbuster", "indie"]
    
    # If current mode is not valid, default to 'balanced'
    if current_critic_mode not in valid_critic_modes:
        current_critic_mode = "balanced"
        # Update the preference to fix the invalid value
        set_critic_mode_pref(current_critic_mode)
    
    new_critic_mode = st.sidebar.selectbox(
        "Critic Style",
        options=valid_critic_modes,
        index=valid_critic_modes.index(current_critic_mode),
        key="sidebar_critic_mode_select",
        label_visibility="collapsed",
        help="Choose which critic's perspective you want"
    )
    
    if new_critic_mode != current_critic_mode:
        if SETTINGS_HANDLER_AVAILABLE:
            handle_settings_change("critic_mode", new_critic_mode)
        else:
            set_critic_mode_pref(new_critic_mode)
            # Clear cache to get fresh recommendations with new critic mode
            st.cache_data.clear()
            st.rerun()
    
    # Quick accessibility toggles
    col1, col2 = st.sidebar.columns(2)
    with col1:
        current_spoiler = is_spoiler_free()
        if st.button("👁️ Spoiler", help="Toggle spoiler protection", use_container_width=True):
            if SETTINGS_HANDLER_AVAILABLE:
                handle_settings_change("spoiler_free", not current_spoiler)
            else:
                set_spoiler_free(not current_spoiler)
                st.rerun()
    
    with col2:
        current_dyslexia = is_dyslexia_mode()
        if st.button("♿ A11y", help="Toggle accessibility mode", use_container_width=True):
            if SETTINGS_HANDLER_AVAILABLE:
                handle_settings_change("dyslexia_mode", not current_dyslexia)
            else:
                set_dyslexia_mode(not current_dyslexia)
                st.rerun()
    
    st.sidebar.divider()

def render_sidebar_navigation():
    """Add navigation items to sidebar including settings"""
    st.sidebar.page_link("pages/page_09_user_settings.py", label="⚙️ Full Settings", icon=None)
    st.sidebar.divider()

def render_app_footer():
    """Theme-aware footer with service status and critic mode"""
    status = "✅ Online" if is_tmdb_available() else "❌ Offline"
    critic_mode = get_critic_mode_pref()
    
    st.markdown(f"""
    <div style="text-align: center; margin-top: 4rem; padding: 1rem; opacity: 0.6;">
        <p>© 2024 MoviePulse | Data from TMDB | Service: {status} | 
        Critic: {CRITIC_MODE_LABELS.get(critic_mode, 'Balanced')} | v2.4</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------- SETTINGS HANDLER -----------------------
def handle_settings_change(setting_type, value):
    """Handle settings changes including critic mode"""
    if setting_type == "theme":
        set_theme(value)
    elif setting_type == "spoiler_free":
        set_spoiler_free(value)
    elif setting_type == "dyslexia_mode":
        set_dyslexia_mode(value)
    elif setting_type == "critic_mode":
        set_critic_mode_pref(value)
        # Clear cache to get fresh recommendations with new critic mode
        st.cache_data.clear()
    st.rerun()

# ----------------------- MAIN EXECUTION -----------------------
if __name__ == "__main__":
    configure_page()
    init_profile()
    check_first_time_user()
    
    # Layout structure
    render_app_header()
    
    # Sidebar components
    with st.sidebar:
        render_sidebar_filters_with_loading()
        render_advanced_search_options()
        render_quick_settings_sidebar()
        render_sidebar_navigation()
            
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