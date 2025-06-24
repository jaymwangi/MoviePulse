# ui_components/MovieGridView.py
import streamlit as st

def MovieGridView(movies_data, columns=4):
    """
    A responsive grid layout for displaying movie tiles
    
    Args:
        movies_data (list): List of movie data dictionaries
        columns (int): Number of columns in the grid (default 4)
    """
    if not movies_data:
        st.warning("No movies to display")
        return
    
    # Create responsive grid
    cols = st.columns(columns)
    
    for index, movie in enumerate(movies_data):
        with cols[index % columns]:
            # Import MovieTile inside the function to avoid circular imports
            from ui_components.MovieTile import MovieTile
            MovieTile(movie)