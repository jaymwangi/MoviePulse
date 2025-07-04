"""
Enhanced Movie Grid View with Lazy Loading and Pagination
-------------------------------------------------------
Features:
- Progressive loading of movie posters (12-20 at a time)
- "Load More" button for infinite scrolling
- Responsive column layout
- Accessibility-aware rendering
- Performance optimizations
"""

import streamlit as st
from typing import List, Optional
from session_utils.state_tracker import get_user_prefs
from core_config.constants import Movie

# Constants
INITIAL_LOAD_COUNT = 12  # Initial number of movies to display
LOAD_MORE_COUNT = 8      # Additional movies per "Load More" click
MAX_COLUMNS = 6          # Maximum grid columns
MIN_COLUMNS = 2          # Minimum grid columns

def MovieGridView(
    movies_data: List[Movie],
    columns: int = 4,
    lazy_load: bool = True,
    show_pagination: bool = True
) -> Optional[int]:
    """
    Responsive movie grid with lazy loading and pagination.
    
    Args:
        movies_data: Complete list of movies to display
        columns: Default number of grid columns
        lazy_load: Whether to enable progressive loading
        show_pagination: Show/hide the "Load More" button
        
    Returns:
        Number of currently displayed movies or None if not lazy loading
    """
    if not movies_data:
        st.warning("No movies to display")
        return None
    
    # Initialize session state for pagination
    if lazy_load and 'movie_grid_state' not in st.session_state:
        st.session_state.movie_grid_state = {
            'display_count': INITIAL_LOAD_COUNT,
            'last_movie_count': 0
        }
    
    # Adjust columns based on user preferences
    prefs = get_user_prefs()
    if prefs.accessibility_mode:
        columns = min(columns, 3)
    columns = max(MIN_COLUMNS, min(MAX_COLUMNS, columns))
    
    # Determine how many movies to display
    if lazy_load:
        display_count = st.session_state.movie_grid_state['display_count']
        movies_to_display = movies_data[:display_count]
    else:
        movies_to_display = movies_data
    
    # Create responsive grid
    grid_cols = st.columns(columns)
    
    # Display movie tiles
    for index, movie in enumerate(movies_to_display):
        with grid_cols[index % columns]:
            # Lazy load images with placeholder
            with st.spinner("Loading poster..."):
                from ui_components.MovieTile import MovieTile
                MovieTile(
                    movie,
                    testid_suffix=f"grid_{index}",
                    lazy_load=lazy_load
                )
    
    # Pagination controls
    if lazy_load and show_pagination and len(movies_data) > display_count:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Load More Movies", key="load_more_btn"):
                st.session_state.movie_grid_state['display_count'] += LOAD_MORE_COUNT
                st.experimental_rerun()
        
        # Show count indicator
        st.caption(f"Showing {min(st.session_state.movie_grid_state['display_count'], len(movies_data))} of {len(movies_data)} movies")

    
    return display_count if lazy_load else None

def reset_pagination():
    """Reset the grid display count when filters change"""
    if 'movie_grid_state' in st.session_state:
        st.session_state.movie_grid_state['display_count'] = INITIAL_LOAD_COUNT