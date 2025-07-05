# ui_components/RecommendationCard.py
import streamlit as st
from service_clients.tmdb_client import tmdb_client

def RecommendationCard(movie, explanation=None, show_explanation=False):
    """
    Displays a movie recommendation card with explanation toggle.
    
    Args:
        movie (dict|Movie): Movie data with required fields
        explanation (str): AI-generated rationale for recommendation
        show_explanation (bool): Whether to expand explanation by default
    """
    with st.container(border=True):
        # Extract data (works with both dict and Movie object)
        movie_id = movie.id if hasattr(movie, 'id') else movie.get('id')
        title = movie.title if hasattr(movie, 'title') else movie.get('title', 'Untitled')
        poster_path = movie.poster_path if hasattr(movie, 'poster_path') else movie.get('poster_path')
        vote_avg = movie.vote_average if hasattr(movie, 'vote_average') else movie.get('vote_average', 0)
        
        # Get genres (handles Genre objects and strings)
        genres = []
        if hasattr(movie, 'genres'):
            genres = [g.name if hasattr(g, 'name') else str(g) for g in movie.genres]
        else:
            genres = movie.get('genres', [])
        
        # Column layout
        col1, col2 = st.columns([1, 3])
        
        # Poster column
        with col1:
            poster_url = tmdb_client._get_poster_url(poster_path, size='w154') if poster_path else None
            st.image(
                poster_url or "media_assets/icons/image-fallback.svg",
                width=120,
                caption=title
            )
        
        # Info column
        with col2:
            st.markdown(f"**{title}**")
            
            # Display year if available
            release_date = movie.release_date if hasattr(movie, 'release_date') else movie.get('release_date')
            if release_date:
                st.caption(f"📅 {release_date[:4]}")
            
            # Display genres (max 2)
            if genres:
                st.caption(f"🎭 {', '.join(genres[:2])}")
            
            # Rating bar
            if vote_avg > 0:
                st.progress(
                    float(vote_avg / 10),
                    text=f"Rating: {vote_avg:.1f}/10"
                )
            
            # --- "Why this rec?" Toggle ---
            if explanation:
                with st.expander("ℹ️ Why this rec?", expanded=show_explanation):
                    st.caption(explanation)
            else:
                # Fallback explanation if none provided
                with st.expander("ℹ️ Why this rec?", expanded=show_explanation):
                    st.caption("This recommendation is based on:")
                    if genres:
                        st.caption(f"- Shared genres: {', '.join(genres[:2])}")
                    if hasattr(movie, 'similarity_score'):
                        st.caption(f"- {movie.similarity_score:.0%} match score")
            
            # Action buttons
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("View details", key=f"view_{movie_id}"):
                    st.session_state['selected_movie'] = movie_id
                    st.rerun()
            with btn_col2:
                if st.button("❤️ Watchlist", key=f"watchlist_{movie_id}"):
                    if 'watchlist' not in st.session_state:
                        st.session_state['watchlist'] = []
                    st.session_state['watchlist'].append(movie_id)
                    st.toast(f"Added {title} to watchlist")