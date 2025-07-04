import logging
import sys
import os
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters
from session_utils.state_tracker import init_session_state, get_active_filters
from media_assets.styles import load_custom_css
from service_clients.tmdb_client import tmdb_client, FallbackStrategy
from ui_components.MovieGridView import MovieGridView
from streamlit.components.v1 import html
import time

# ----------------------- LOGGING CONFIGURATION -----------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "moviepulse.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_api_call(endpoint: str, params: Dict, duration: float, success: bool):
    """Structured logging for API calls"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "params": params,
        "duration_sec": round(duration, 3),
        "status": "success" if success else "failed",
        "service": "TMDB"
    }
    logger.info(f"API_CALL: {log_data}")

def log_user_action(action: str, metadata: Dict = None):
    """Log user interactions"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "session_id": st.session_state.get('session_id', 'unknown'),
        "metadata": metadata or {}
    }
    logger.info(f"USER_ACTION: {log_entry}")

# ----------------------- CACHED FUNCTIONS -----------------------
@st.cache_data(ttl=600, show_spinner="Searching movies...")
def cached_search(query: str, filters: Dict = None, page: int = 1) -> Tuple[List[Dict], int]:
    """Cache search results with comprehensive logging"""
    search_start = time.perf_counter()
    log_user_action("search_initiated", {"query": query, "page": page})
    
    try:
        if not tmdb_client:
            raise RuntimeError("TMDB service unavailable")
            
        results, total_pages = tmdb_client.search_movies(
            query=query,
            filters=filters,
            fallback_strategy=FallbackStrategy.RELAX_GRADUAL,
            page=page
        )
        
        duration = time.perf_counter() - search_start
        log_api_call("search/movie", {"query": query, "page": page}, duration, True)
        log_user_action("search_completed", {
            "query": query,
            "result_count": len(results),
            "duration_sec": round(duration, 3)
        })
        
        return results, total_pages
        
    except Exception as e:
        duration = time.perf_counter() - search_start
        logger.error(f"Search failed for '{query}': {str(e)}", exc_info=True)
        log_api_call("search/movie", {"query": query, "page": page}, duration, False)
        raise

@st.cache_data(ttl=86400)
def get_cached_genres() -> List[Dict]:
    """Cache genre list with logging"""
    logger.info("Fetching genres from TMDB")
    try:
        genres = tmdb_client.get_genres()
        logger.info(f"Successfully fetched {len(genres)} genres")
        return genres
    except Exception as e:
        logger.error(f"Failed to fetch genres: {str(e)}", exc_info=True)
        return []

# ----------------------- PAGE COMPONENTS -----------------------
def initialize_session() -> None:
    """Initialize all session state variables with logging"""
    init_start = time.perf_counter()
    logger.info("Initializing session state")
    
    init_session_state()
    required_states = {
        'current_page': 1,
        'search_history': [],
        'global_search_query': "",
        'filters_changed': False,
        'last_api_call': None
    }
    
    for key, default in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = default
            logger.debug(f"Initialized session state: {key} = {default}")
    
    logger.info(f"Session initialized in {time.perf_counter() - init_start:.3f}s")

def render_search_page() -> None:
    """Main search page with comprehensive logging"""
    page_start = time.perf_counter()
    logger.info("Rendering search page")
    
    try:
        if not tmdb_client:
            logger.error("TMDB service unavailable on page render")
            st.error("TMDB service is currently unavailable")
            if st.button("Retry Connection"):
                log_user_action("service_retry")
                st.rerun()
            return
        
        initialize_session()
        load_custom_css()
        
        if 'genres' not in st.session_state:
            with st.spinner("Loading genres..."):
                st.session_state.genres = get_cached_genres()
        
        render_app_header()
        render_search_controls()
        
        with st.container():
            if st.session_state.get("global_search_query"):
                display_search_results()
            else:
                show_empty_state()
                
        logger.info(f"Page rendered in {time.perf_counter() - page_start:.3f}s")
        
    except Exception as e:
        logger.error(f"Page render failed: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred")
        if st.button("Reload Page"):
            st.rerun()

def render_search_controls() -> None:
    """Render search controls with interaction logging"""
    logger.debug("Rendering search controls")
    
    with st.container():
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            search_input = st.text_input(
                "🔍 Search movies, actors, or moods...",
                value=st.session_state.get("global_search_query", ""),
                key="search_input_field",
                help="Try 'mind-bending sci-fi' or 'Scorsese films'",
                label_visibility="collapsed"
            )
            
            if search_input != st.session_state.get("global_search_query"):
                log_user_action("search_query_changed", {
                    "old_query": st.session_state.get("global_search_query"),
                    "new_query": search_input
                })
                st.session_state.global_search_query = search_input
                st.session_state.current_page = 1
                if search_input and search_input not in st.session_state.search_history:
                    st.session_state.search_history.append(search_input)
                st.rerun()
    
    with st.sidebar:
        render_sidebar_filters()
        render_search_history()

def render_search_history() -> None:
    """Render search history with interaction logging"""
    if st.session_state.search_history:
        with st.expander("🔍 Recent Searches"):
            for query in reversed(st.session_state.search_history[-5:]):
                if st.button(query, use_container_width=True):
                    log_user_action("history_search_selected", {"query": query})
                    st.session_state.global_search_query = query
                    st.session_state.current_page = 1
                    st.rerun()

def display_search_results() -> None:
    """Display search results with comprehensive logging"""
    query = st.session_state.get("global_search_query", "")
    logger.info(f"Displaying results for query: '{query}'")
    
    try:
        filters = get_active_filters()
        log_user_action("search_executed", {
            "query": query,
            "page": st.session_state.current_page,
            "filters": filters
        })
        
        with st.spinner(f"🔍 Searching for '{query}'..."):
            movies, total_pages = cached_search(
                query=query,
                filters=filters,
                page=st.session_state.current_page
            )
            
            st.subheader(f"Results for: '{query}'", divider="red")
            
            if not movies:
                logger.warning(f"No results found for query: '{query}'")
                st.warning("No results found matching your criteria")
                if st.button("Try Relaxing Filters"):
                    log_user_action("relax_filters_clicked")
                    st.session_state.search_fallback_strategy = FallbackStrategy.RELAX_ALL
                    st.rerun()
                return
            
            if total_pages > 1:
                cols = st.columns([0.2, 0.6, 0.2])
                with cols[0]:
                    if st.session_state.current_page > 1 and st.button("⬅️ Previous"):
                        log_user_action("pagination_previous")
                        st.session_state.current_page -= 1
                        st.rerun()
                with cols[1]:
                    st.markdown(f"**Page {st.session_state.current_page} of {total_pages}**")
                with cols[2]:
                    if st.session_state.current_page < total_pages and st.button("Next ➡️"):
                        log_user_action("pagination_next")
                        st.session_state.current_page += 1
                        st.rerun()
            
            MovieGridView(movies, columns=4)
            
    except Exception as e:
        logger.error(f"Failed to display results for '{query}': {str(e)}", exc_info=True)
        st.error(f"Failed to fetch results: {str(e)}")
        if st.button("🔄 Retry Search"):
            log_user_action("search_retry")
            st.rerun()

def show_empty_state() -> None:
    """Show empty search state with usage analytics"""
    log_user_action("empty_state_viewed")
    st.markdown("""
    <div style="text-align: center; margin-top: 5rem;">
        <h3 style="color: #FF4B4B;">🔍 Find Your Next Favorite Movie</h3>
        <p style="opacity: 0.8;">
            Search by title, actor, director, or mood<br>
            Try "Christopher Nolan" or "80s sci-fi"
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💡 Search Tips", expanded=True):
        st.markdown("""
        - **Quotes** for exact matches: `"The Dark Knight"`
        - **Year ranges**: `2010..2020`
        - **Combinations**: `Scorsese crime 1990s`
        """)

# ----------------------- MAIN EXECUTION -----------------------
if __name__ == "__main__":
    try:
        logger.info("Starting MoviePulse application")
        render_search_page()
        logger.info("Application completed successfully")
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}", exc_info=True)
        st.error("A critical error occurred. Please refresh the page.")
