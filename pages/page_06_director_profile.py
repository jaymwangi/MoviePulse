"""
Director Profile Page
---------------------
Displays comprehensive information about a director including:
- Biography and personal details
- Complete filmography (directed movies and other roles)
- Responsive layout with back navigation
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime
from service_clients.tmdb_client import tmdb_client
from session_utils.state_tracker import get_current_director
from ui_components.MovieGridView import MovieGridView as render_movie_grid
from ui_components.Navigation import back_button
from ui_components.HeaderBar import render_app_header
from media_assets.styles.main import initialize_theme

def director_profile_page():
    """Main director profile page with detailed filmography"""
    # Initialize page config and styles
    st.set_page_config(
        page_title="Director Profile | MoviePulse",
        page_icon="🎞️",
        layout="wide"
    )
    initialize_theme()
    
    # Get director data from session state
    director = get_current_director()
    if not director:
        st.error("Director information not found. Please navigate from a movie page.")
        st.stop()
    
    # Fetch additional director details from TMDB
    try:
        director_details = tmdb_client.get_director_details(director.get("id"))
        if director_details:
            director.update(director_details)
    except Exception as e:
        st.warning(f"Couldn't load director details: {str(e)}")
    
    # Page Header with Back Navigation
    _render_page_header(director)
    
    # Main content columns
    info_col, content_col = st.columns([1, 3], gap="large")
    
    with info_col:
        _render_director_sidebar(director)
    
    with content_col:
        _render_director_content(director)

def _render_page_header(director: Dict) -> None:
    """Render page header with back button and title"""
    render_app_header()
    
    col1, col2 = st.columns([1, 10])
    with col1:
        back_button(
            target_page="page_03_movie_details",
            label="← Back to Movie",
            use_container_width=True
        )
    with col2:
        st.title(f"{director.get('name', 'Unknown Director')}")

def _render_director_sidebar(director: Dict) -> None:
    """Render director metadata sidebar"""
    st.subheader("Director Details")
    
    # Profile image with fallback
    profile_path = director.get("profile_path")
    img_url = (
        f"https://image.tmdb.org/t/p/w300{profile_path}" 
        if profile_path 
        else "media_assets/icons/person_placeholder.png"
    )
    st.image(img_url, use_column_width=True)
    
    # Metadata display
    metadata_items = [
        ("Known For", director.get("known_for_department")),
        ("Born", _format_date(director.get("birthday"))),
        ("Birth Place", director.get("place_of_birth")),
        ("Died", _format_date(director.get("deathday"))),
        ("TMDB ID", director.get("id"))
    ]
    
    for label, value in metadata_items:
        if value:
            st.markdown(f"**{label}:** {value}")

def _render_director_content(director: Dict) -> None:
    """Render main content area with filmography"""
    # Biography section
    st.subheader("Biography")
    biography = director.get("biography", "No biography available.")
    st.markdown(biography if biography else "*No biography available*")
    
    # Filmography section
    st.subheader("Filmography")
    try:
        filmography = tmdb_client.get_director_filmography(director.get("id"))
    except Exception as e:
        st.error(f"Couldn't load filmography: {str(e)}")
        return
    
    if not filmography:
        st.info("No filmography data available")
        return
    
    # Separate directed movies from other roles
    directed_movies = [m for m in filmography if m.get("job") == "Director"]
    other_roles = [m for m in filmography if m.get("job") != "Director"]
    
    # Directed movies section
    st.markdown("#### Directed Movies")
    if directed_movies:
        render_movie_grid(
            movies_data=directed_movies,
            columns=4,
            lazy_load=False,
            show_pagination=False
        )
    else:
        st.info("No directing credits found")
    
    # Other roles section (if any)
    if other_roles:
        st.markdown(f"#### Other Crew Roles ({len(other_roles)})")
        
        # Group by role type
        role_groups = {}
        for movie in other_roles:
            role = movie.get("job", "Other")
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(movie)
        
        # Display each role group in expanders
        for role, movies in role_groups.items():
            with st.expander(f"{role} ({len(movies)})"):
                render_movie_grid(
                    movies_data=movies,
                    columns=3,
                    lazy_load=True,
                    show_pagination=False
                )

def _format_date(date_str: Optional[str]) -> Optional[str]:
    """Format date string for display"""
    if not date_str:
        return None
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%B %d, %Y")
    except ValueError:
        return date_str

if __name__ == "__main__":
    director_profile_page()