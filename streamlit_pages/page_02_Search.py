# streamlit_pages/02_Search.py
import streamlit as st
from ui_components.HeaderBar import render_app_header
from ui_components.SidebarFilters import render_sidebar_filters
from session_utils.state_tracker import init_session_state, get_active_filters
from media_assets.styles import load_custom_css

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
    """Displays search results grid (placeholder for now)"""
    st.subheader(f"Results for: '{st.session_state.global_search_query}'", 
                divider="red")
    
    # Placeholder results - will connect to TMDB API later
    cols = st.columns(4)
    for i in range(8):
        with cols[i % 4]:
            st.image(
                f"media_assets/posters/placeholder_{i%5+1}.png",
                use_container_width=True,
                caption=f"Result {i+1}"
            )
            st.markdown(f"**Movie Title {i+1}**")
            st.caption(f"202{i%5} • ⭐ {7+i%3}.{i%2}")

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