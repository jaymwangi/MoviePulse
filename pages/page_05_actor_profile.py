import streamlit as st
from service_clients.tmdb_client import tmdb_client
from session_utils.state_tracker import init_session_state
from app_ui.components.MovieTile import MovieTile
from ui_components.CastList import CastList
import media_assets.styles.main as styles
from datetime import datetime

# Initialize session state
init_session_state()

def show_actor_header(actor):
    """Display actor header with image and metadata"""
    with st.container():
        col1, col2 = st.columns([1, 3], gap="large")
        with col1:
            profile_url = (
                f"https://image.tmdb.org/t/p/original{actor.profile_path}" 
                if actor.profile_path 
                else "media_assets/icons/person_placeholder.png"
            )
            st.image(
                profile_url,
                width=300,
                use_column_width=True,
                output_format="auto",
                # Apply the actor-image class from main styles
                caption=f"Photo of {actor.name}",
            )

        with col2:
            st.title(actor.name)
            st.caption(f"*{actor.biography or 'No biography available'}*")
            
            # Metadata row using columns for better mobile responsiveness
            st.markdown('<div class="actor-metadata">', unsafe_allow_html=True)
            cols = st.columns(3)
            with cols[0]:
                st.metric("Known For", actor.known_for_department or "Acting")
            with cols[1]:
                st.metric("Birthday", actor.birthday or "Unknown")
            with cols[2]:
                st.metric("Place of Birth", actor.place_of_birth or "Unknown")
            st.markdown('</div>', unsafe_allow_html=True)

def show_filmography(actor_id):
    """Display actor's filmography with department grouping"""
    with st.container():
        st.subheader("Filmography")
        
        with st.spinner("Loading filmography..."):
            credits = tmdb_client.get_actor_filmography(actor_id)
        
        if not credits:
            st.warning("No filmography data available")
            return
        
        # Group by department if available
        departments = {credit.department for credit in credits if credit.department}
        if departments:
            for dept in sorted(departments):
                with st.expander(f"{dept} Credits ({len([c for c in credits if c.department == dept])})"):
                    show_movie_grid([credit for credit in credits if credit.department == dept])
        else:
            show_movie_grid(credits)

def show_movie_grid(movies):
    """Display movie grid using your existing MovieTile component"""
    cols = st.columns(4)
    for idx, movie in enumerate(movies[:12]):  # Limit to 12 for mobile
        with cols[idx % 4]:
            MovieTile(
                movie_data=movie,
                show_details=True,
                testid_suffix=f"filmography_{movie.id}",
                lazy_load=True
            )

def main():
    # Load all necessary styles from main styles module
    styles.load_actor_page_styles()
    
    # Navigation Control
    if "current_actor" not in st.session_state:
        st.error("No actor selected")
        st.page_link("pages/page_03_movie_details.py", label="← Back to Movie")
        return
    
    actor_id = st.session_state["current_actor"]
    
    try:
        # Back button at top - styled using the global back-button class
        if st.button("← Back to Movie", 
                    key="actor_back_top", 
                    use_container_width=True,
                    help="Return to the movie details page"):
            st.session_state.pop("current_actor", None)
            st.switch_page("pages/page_03_movie_details.py")
        
        # Fetch actor details with loading state
        with st.spinner(f"Loading {st.session_state.get('actor_name', 'actor')} details..."):
            actor = tmdb_client.get_person_details(actor_id)
        
        # Page Content
        show_actor_header(actor)
        show_filmography(actor_id)
        
        # Back button at bottom
        st.divider()
        if st.button("← Back to Movie", 
                    key="actor_back_bottom", 
                    use_container_width=True,
                    help="Return to the movie details page"):
            st.session_state.pop("current_actor", None)
            st.switch_page("pages/page_03_movie_details.py")
            
    except Exception as e:
        st.error(f"Failed to load actor details: {str(e)}")
        if st.button("← Back to Movie", 
                    key="actor_error_back", 
                    use_container_width=True):
            st.session_state.pop("current_actor", None)
            st.switch_page("pages/page_03_movie_details.py")

if __name__ == "__main__":
    main()