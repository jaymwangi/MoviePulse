import streamlit as st
from typing import List, Optional, Dict, Union
from session_utils.state_tracker import get_user_prefs
from core_config.constants import Movie
from app_ui.components.MovieTile import MovieTile

# Constants
INITIAL_LOAD_COUNT = 12
LOAD_MORE_COUNT = 8
MAX_COLUMNS = 6
MIN_COLUMNS = 2
DEFAULT_COLUMNS = 4

class MovieGridView:
    
    @staticmethod
    def _get_column_count(prefs: Dict) -> int:
        """Responsive column calculation with accessibility support"""
        if prefs.get('accessibility_mode', False):
            return min(3, DEFAULT_COLUMNS)
        return DEFAULT_COLUMNS

    @staticmethod
    def render(
        movies_data: List[Union[Movie, Dict]],
        columns: Optional[int] = None,
        lazy_load: bool = True,
        show_pagination: bool = True,
        reset_state: bool = False
    ) -> Optional[int]:
        """
        Optimized movie grid renderer with pixel-perfect spacing and consistent metadata layout.
        
        Args:
            movies_data: List of Movie objects/dicts
            columns: Optional fixed column count
            lazy_load: Enable progressive loading
            show_pagination: Show load more button
            reset_state: Reset pagination state
            
        Returns:
            Number of displayed movies or None if showing all
        """
        if not movies_data:
            st.warning("No movies to display")
            return None

        # State management
        if reset_state or 'movie_grid_state' not in st.session_state:
            MovieGridView.reset_state()

        # Responsive column calculation
        grid_columns = columns if columns is not None else MovieGridView._get_column_count(get_user_prefs())
        grid_columns = max(MIN_COLUMNS, min(MAX_COLUMNS, grid_columns))

        # Display logic
        display_count = (
            st.session_state.movie_grid_state['display_count']
            if lazy_load else len(movies_data)
        )

        movies_to_display = movies_data[:display_count]

        # Grid container with optimized spacing
        with st.container():
            # CSS for tight grid layout with consistent metadata height
            st.markdown(f"""
            <style>
                [data-testid="column"] {{
                    padding: 0.25rem !important;
                }}
                [data-testid="stHorizontalBlock"] {{
                    gap: 0.5rem !important;
                }}
                
                /* Ensure consistent height for all movie tiles */
                .movie-tile-container {{
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                }}
                
                /* Fixed height for poster container */
                .movie-poster-container {{
                    flex: 0 0 auto;
                }}
                
                /* Metadata section with consistent spacing */
                .movie-metadata-section {{
                    flex: 1 1 auto;
                    min-height: 120px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    padding: 8px 4px 0;
                }}
                
                /* Genre tags container with fixed max height */
                .movie-genres-container {{
                    min-height: 32px;
                    margin-top: 8px;
                }}
            </style>
            """, unsafe_allow_html=True)

            # Create columns with minimal gap
            cols = st.columns(grid_columns, gap="small")

            # Render movies
            for idx, movie in enumerate(movies_to_display):
                with cols[idx % grid_columns]:
                    # Wrap in container for consistent height
                    st.markdown('<div class="movie-tile-container">', unsafe_allow_html=True)
                    MovieTile(
                        movie,
                        testid_suffix=f"grid_{idx}",
                        lazy_load=lazy_load
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

        # Pagination controls
        if lazy_load and show_pagination and len(movies_data) > display_count:
            st.markdown("---")
            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button("Load More Movies", 
                           key="load_more_btn",
                           use_container_width=True):
                    st.session_state.movie_grid_state['display_count'] += LOAD_MORE_COUNT
                    st.session_state.movie_grid_state['current_page'] += 1
                    st.rerun()

            st.caption(
                f"Showing {min(display_count, len(movies_data))} of {len(movies_data)} movies • "
                f"Page {st.session_state.movie_grid_state['current_page']}"
            )

        return display_count if lazy_load else None

    @staticmethod
    def reset_state():
        """Reset grid pagination to initial state"""
        st.session_state.movie_grid_state = {
            'display_count': INITIAL_LOAD_COUNT,
            'current_page': 1
        }