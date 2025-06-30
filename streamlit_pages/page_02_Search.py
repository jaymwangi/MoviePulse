# streamlit_pages/02_Search.py
import streamlit as st
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters
from session_utils.state_tracker import init_session_state, get_active_filters
from media_assets.styles import load_custom_css
from service_clients.tmdb_client import tmdb_client

def render_search_page():
    """Main search page layout with results display logic"""
    # Initialize session state and styles
    init_session_state()
    load_custom_css()
    
    # Render core UI components
    render_app_header()
    render_sidebar_filters()
    
    # Main content area
    with st.container():
        # Display search results if query exists
        if st.session_state.get("global_search_query"):
            display_search_results()
        else:
            show_empty_state()

def display_search_results():
    query = st.session_state.get("global_search_query", "")
    filters = st.session_state.get("filters", {})
    if not query:
        st.warning("No query provided")
        return

    try:
        movies, total_pages = tmdb_client.search_movies(query, filters)
        st.subheader(f"Results for: '{query}'", divider="red")

        if not movies:
            st.warning("No results found.")
            return

        cols = st.columns(4)
        for i, movie in enumerate(movies):
            with cols[i % 4]:
                st.image(
                    movie.poster_path or "media_assets/posters/default.png",
                    use_container_width=True
                )
                st.markdown(f"**{movie.title}**")
                st.caption(f"{movie.release_date[:4] if movie.release_date else 'N/A'} • ⭐ {movie.vote_average}")
    except Exception as e:
        st.error(f"Failed to fetch results: {e}")


def show_empty_state():
    """Shows the empty search state with guidance"""
    st.markdown("""
    <div style="text-align: center; margin-top: 5rem;">
        <h3 style="color: #FF4B4B;">🔍 Find Your Next Favorite Movie</h3>
        <p style="opacity: 0.8;">
            Search by title, actor, director, or mood<br>
            Try "Christopher Nolan" or "80s sci-fi"
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Animated search prompt
    with st.expander("💡 Search Tips", expanded=True):
        st.markdown("""
        - **Quotes** for exact matches: `"The Dark Knight"`
        - **Year ranges**: `2010..2020`
        - **Combinations**: `Scorsese crime 1990s`
        """)

# Page entry point
if __name__ == "__main__":
    render_search_page()