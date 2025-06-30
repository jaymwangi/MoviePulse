# ui_components/MovieGridView.py
import streamlit as st
from session_utils.state_tracker import get_user_prefs

def MovieGridView(movies_data, columns=4):
    """
    A responsive grid layout for displaying movie tiles with navigation support
    
    Args:
        movies_data (list): List of movie data dictionaries/objects
        columns (int): Number of columns in the grid (default 4)
    """
    if not movies_data:
        st.warning("No movies to display")
        return
    
    # Adjust columns based on user preferences
    prefs = get_user_prefs()
    if prefs.accessibility_mode:
        columns = min(columns, 3)  # Fewer columns for better accessibility
    
    # Create responsive grid
    cols = st.columns(columns)
    
    for index, movie in enumerate(movies_data):
        with cols[index % columns]:
            # Import MovieTile inside the function to avoid circular imports
            from ui_components.MovieTile import MovieTile
            MovieTile(
                movie,
                testid_suffix=f"grid_{index}"  # Unique test IDs for grid items
            )