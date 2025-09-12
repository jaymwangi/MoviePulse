import streamlit as st
from session_utils.watchlist_manager import load_watchlist
from app_ui.components import MovieTile  # Assuming you have a MovieTile component

def render_watchlist_grid():
    """Display watchlist movies in a responsive grid"""
    user_id = st.session_state.get("user_id", "anonymous")
    watchlist_data = load_watchlist().get(user_id, {}).get("movies", [])
    
    if not watchlist_data:
        st.info("Your watchlist is empty. Add movies to see them here!")
        return
    
    # Responsive grid - adjust columns based on screen size
    cols = st.columns(4)  # Default to 4 columns
    
    for idx, movie in enumerate(watchlist_data):
        with cols[idx % 4]:
            MovieTile.display(
                movie_id=movie["movie_id"],
                title=movie["title"],
                poster_path=movie["poster_path"],
                show_actions=True
            )
