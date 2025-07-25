# -*- coding: utf-8 -*-
import streamlit as st
from ui_components.BadgeProgress import BadgeProgress
from session_utils.user_profile import update_cinephile_stats, get_user_id, load_current_profile
from service_clients.tmdb_client import tmdb_client

def show_cinephile_filters():
    """Render cinephile-specific filters in sidebar with improved layout"""
    with st.sidebar:
        st.header("🎬 Cinephile Mode")
        
        # Core filters with better organization
        with st.expander("Filter Options", expanded=True):
            st.checkbox(
                "🌎 Foreign Films Only", 
                key="cinephile_foreign",
                help="Only show non-English language films"
            )
            
            st.checkbox(
                "🏛 Criterion Collection", 
                key="cinephile_criterion",
                help="Focus on Criterion-approved films"
            )
            
            st.slider(
                "⭐ Min Critic Score", 
                min_value=60, 
                max_value=100, 
                value=85,
                key="cinephile_min_score",
                help="Filter by Rotten Tomatoes score"
            )

def filter_movies(movie_list):
    """Apply cinephile filters to movie results with better error handling"""
    if not movie_list:
        return []
    
    try:
        filtered = movie_list.copy()
        
        if st.session_state.get("cinephile_foreign"):
            filtered = [m for m in filtered if m.get("original_language") != "en"]
        
        if st.session_state.get("cinephile_criterion"):
            filtered = [m for m in filtered if m.get("belongs_to_collection", False)]
        
        if st.session_state.get("cinephile_min_score"):
            min_score = st.session_state.cinephile_min_score
            filtered = [m for m in filtered if m.get("vote_average", 0) * 10 >= min_score]
        
        return filtered
    except Exception as e:
        st.error(f"Error applying filters: {str(e)}")
        return movie_list  # Return original list if filtering fails

def show_badge_progress():
    """Display achievement tracking with improved layout"""
    try:
        st.header("Your Cinephile Journey")
        
        # Get user stats from profile
        profile = load_current_profile()
        user_stats = profile.get("badge_progress", {})
        
        # Initialize and display badges with tier filtering
        badge_component = BadgeProgress(get_user_id())
        
        # Add tier filter selector
        tier_filter = st.selectbox(
            "Filter by Tier",
            ["All", "Bronze", "Silver", "Gold"],
            index=0
        )
        
        # Display badges
        badge_component.display_badge_progress(
            user_stats,
            filter_tier=None if tier_filter == "All" else tier_filter.lower(),
            columns_per_row=3
        )
        
    except Exception as e:
        st.error(f"Couldn't load badge progress: {str(e)}")

def main():
    # Configure page settings
    st.set_page_config(
        page_title="Cinephile Mode | MoviePulse",
        page_icon="🎞️",
        layout="wide"
    )
    
    # Initialize session state with default values
    session_defaults = {
        "cinephile_foreign": False,
        "cinephile_criterion": False,
        "cinephile_min_score": 85
    }
    
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Display filters in sidebar
    show_cinephile_filters()
    
    # Main content area
    with st.container():
        st.title("Cinephile Mode")
        st.markdown("Discover and track high-quality films that match your cinematic tastes.")
        
        # Updated sample movie data with valid TMDB IDs
        sample_movies = [
            {
                "id": 496243,  # Parasite (2019)
                "title": "Parasite", 
                "original_language": "ko", 
                "vote_average": 8.5, 
                "belongs_to_collection": True,
                "poster_path": "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"
            },
            {
                "id": 238,  # The Godfather (1972)
                "title": "The Godfather", 
                "original_language": "en", 
                "vote_average": 9.2, 
                "belongs_to_collection": True,
                "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg"
            },
            {
                "id": 155,  # The Dark Knight (2008)
                "title": "The Dark Knight", 
                "original_language": "en", 
                "vote_average": 8.5, 
                "belongs_to_collection": False,
                "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg"
            }
        ]
        
        # Apply filters
        filtered_movies = filter_movies(sample_movies)
        
        # Display results with better error handling
        if not filtered_movies:
            st.warning("No movies match your current filters. Try adjusting your criteria.")
        else:
            st.header("Curated Selection")
            cols = st.columns(3)  # 3-column layout
            
            for idx, movie in enumerate(filtered_movies):
                with cols[idx % 3]:
                    with st.container(border=True):
                        # Use actual poster if available, otherwise placeholder
                        poster_url = (
                            f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" 
                            if movie.get("poster_path") 
                            else "https://via.placeholder.com/300x450"
                        )
                        
                        st.image(poster_url, use_container_width=True)
                        st.subheader(movie["title"])
                        st.caption(f"Score: {movie['vote_average'] * 10:.0f}%")
                        
                        if st.button("View Details", key=f"details_{movie['id']}"):
                            try:
                                update_cinephile_stats(movie['id'])
                                st.rerun()  # Refresh to show updated badges
                            except Exception as e:
                                st.error(f"Couldn't update stats: {str(e)}")
        
        # Show badge progress at the bottom
        show_badge_progress()

if __name__ == "__main__":
    main()