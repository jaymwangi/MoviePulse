# app_ui/components/FilterBar.py

import streamlit as st
from typing import List, Optional, Callable, Dict, Any

class FilterBar:
    """A reusable filter bar component with genre, mood, and rating filters."""
    
    def __init__(self, filter_changed_callback: Optional[Callable] = None):
        """
        Initialize the FilterBar component.
        
        Args:
            filter_changed_callback: Optional callback function to be called when filters change
        """
        self.filter_changed_callback = filter_changed_callback
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for filters if not already set."""
        if 'filters' not in st.session_state:
            st.session_state.filters = {
                'genres': [],
                'moods': [],
                'min_rating': 0,
                'max_rating': 10,
                'year_range': [1900, 2023]  # Default year range
            }
    
    def render(self, available_genres: List[str], available_moods: List[str]):
        """
        Render the filter bar component.
        
        Args:
            available_genres: List of available genres to filter by
            available_moods: List of available moods to filter by
        """
        # Container for the filter bar
        with st.container():
            st.markdown("### 🎛️ Filters")
            
            # Two-column layout for filters
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Genre filter chips
                st.markdown("**Genre**")
                self._render_chip_filter("genres", available_genres, "🎭")
                
                # Mood filter chips
                st.markdown("**Mood**")
                self._render_chip_filter("moods", available_moods, "😊")
            
            with col2:
                # Rating slider
                st.markdown("**Rating**")
                min_rating, max_rating = st.slider(
                    "Select rating range:",
                    min_value=0,
                    max_value=10,
                    value=(st.session_state.filters['min_rating'], st.session_state.filters['max_rating']),
                    step=1,
                    format="%d ⭐",
                    key="rating_slider",
                    label_visibility="collapsed"
                )
                
                # Year range slider (optional)
                st.markdown("**Year**")
                min_year, max_year = st.slider(
                    "Select year range:",
                    min_value=1900,
                    max_value=2023,
                    value=(st.session_state.filters['year_range'][0], st.session_state.filters['year_range'][1]),
                    step=1,
                    format="%d",
                    key="year_slider",
                    label_visibility="collapsed"
                )
            
            # Update session state if filters changed
            if (min_rating != st.session_state.filters['min_rating'] or 
                max_rating != st.session_state.filters['max_rating']):
                st.session_state.filters['min_rating'] = min_rating
                st.session_state.filters['max_rating'] = max_rating
                self._trigger_callback()
            
            if (min_year != st.session_state.filters['year_range'][0] or 
                max_year != st.session_state.filters['year_range'][1]):
                st.session_state.filters['year_range'] = [min_year, max_year]
                self._trigger_callback()
    
    def _render_chip_filter(self, filter_type: str, options: List[str], emoji_prefix: str):
        """
        Render a chip-based filter for genres or moods.
        
        Args:
            filter_type: Type of filter ('genres' or 'moods')
            options: List of available options
            emoji_prefix: Emoji to prefix each option with
        """
        # Create columns for the chips (4 chips per row)
        cols = st.columns(4)
        current_filters = st.session_state.filters.get(filter_type, [])
        
        for idx, option in enumerate(options):
            col_idx = idx % 4
            is_selected = option in current_filters
            
            # Determine button label with emoji
            button_label = f"{emoji_prefix} {option}"
            
            # Toggle selection when clicked
            if cols[col_idx].button(
                button_label,
                key=f"{filter_type}_{option}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                if is_selected:
                    # Remove from filters
                    st.session_state.filters[filter_type].remove(option)
                else:
                    # Add to filters
                    st.session_state.filters[filter_type].append(option)
                
                self._trigger_callback()
    
    def _trigger_callback(self):
        """Trigger the filter changed callback if provided."""
        if self.filter_changed_callback:
            self.filter_changed_callback(st.session_state.filters)
    
    def get_active_filters(self) -> Dict[str, Any]:
        """Get the currently active filters."""
        return st.session_state.filters.copy()
    
    def clear_filters(self):
        """Clear all active filters."""
        st.session_state.filters = {
            'genres': [],
            'moods': [],
            'min_rating': 0,
            'max_rating': 10,
            'year_range': [1900, 2023]
        }
        self._trigger_callback()
    
    def apply_filters(self, movies_data: List[Dict]) -> List[Dict]:
        """
        Apply current filters to a list of movies.
        
        Args:
            movies_data: List of movie dictionaries to filter
            
        Returns:
            Filtered list of movies
        """
        filtered_movies = movies_data.copy()
        filters = st.session_state.filters
        
        # Filter by genre
        if filters['genres']:
            filtered_movies = [
                movie for movie in filtered_movies 
                if any(genre in movie.get('genres', []) for genre in filters['genres'])
            ]
        
        # Filter by mood
        if filters['moods']:
            filtered_movies = [
                movie for movie in filtered_movies 
                if any(mood in movie.get('moods', []) for mood in filters['moods'])
            ]
        
        # Filter by rating
        filtered_movies = [
            movie for movie in filtered_movies 
            if filters['min_rating'] <= movie.get('rating', 0) <= filters['max_rating']
        ]
        
        # Filter by year
        filtered_movies = [
            movie for movie in filtered_movies 
            if filters['year_range'][0] <= movie.get('year', 1900) <= filters['year_range'][1]
        ]
        
        return filtered_movies

# Example usage function
def demo_filter_bar():
    """Demonstrate how to use the FilterBar component."""
    st.title("FilterBar Component Demo")
    
    # Sample data
    sample_movies = [
        {'title': 'Movie 1', 'genres': ['Action', 'Adventure'], 'moods': ['Exciting', 'Epic'], 'rating': 8, 'year': 2020},
        {'title': 'Movie 2', 'genres': ['Comedy', 'Romance'], 'moods': ['Funny', 'Heartwarming'], 'rating': 7, 'year': 2019},
        {'title': 'Movie 3', 'genres': ['Drama'], 'moods': ['Thoughtful', 'Emotional'], 'rating': 9, 'year': 2021},
        {'title': 'Movie 4', 'genres': ['Action', 'Thriller'], 'moods': ['Suspenseful', 'Exciting'], 'rating': 6, 'year': 2018},
    ]
    
    available_genres = ['Action', 'Adventure', 'Comedy', 'Drama', 'Romance', 'Thriller']
    available_moods = ['Exciting', 'Epic', 'Funny', 'Heartwarming', 'Thoughtful', 'Emotional', 'Suspenseful']
    
    # Create filter bar instance
    filter_bar = FilterBar()
    
    # Render the filter bar
    filter_bar.render(available_genres, available_moods)
    
    # Show clear filters button
    if st.button("Clear All Filters"):
        filter_bar.clear_filters()
        st.rerun()
    
    # Display active filters
    st.subheader("Active Filters")
    st.json(filter_bar.get_active_filters())
    
    # Apply filters and show results
    filtered_movies = filter_bar.apply_filters(sample_movies)
    
    st.subheader(f"Filtered Results ({len(filtered_movies)} movies)")
    for movie in filtered_movies:
        st.write(f"- {movie['title']} ({movie['year']}) - ⭐{movie['rating']}")

if __name__ == "__main__":
    demo_filter_bar()