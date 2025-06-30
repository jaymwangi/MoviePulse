# streamlit_pages/3_🎬_MovieDetails.py
import streamlit as st
from service_clients.tmdb_client import tmdb_client
from ui_components import CastList, SmartTagDisplay
from session_utils.state_tracker import (
    get_watchlist,
    update_watchlist,
    get_user_prefs
)
from datetime import datetime

def _format_runtime(minutes: int) -> str:
    """Convert runtime minutes to HHh MMm format"""
    if not minutes:
        return ""
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if hours else f"{mins}m"

def _is_in_watchlist(movie_id: int) -> bool:
    """Check if movie exists in watchlist"""
    return any(m.get('id') == movie_id for m in get_watchlist())

def run():
    # 1. Get movie ID from URL
    movie_id = st.query_params.get("id", "")
    if not movie_id or not movie_id.isdigit():
        st.error("Invalid movie selection")
        st.page_link("pages/1_🏠_Home.py", label="← Back to Home")
        return
    
    movie_id = int(movie_id)
    
    # 2. Fetch data using existing TMDB client
    try:
        with st.spinner("Loading cinematic details..."):
            details = tmdb_client.get_movie_details_extended(movie_id)
            videos = tmdb_client.get_movie_videos(movie_id)
            
            # Apply user preferences
            prefs = get_user_prefs()
            if prefs.dyslexia_font:
                st.markdown("""
                <style>
                    * {
                        font-family: 'OpenDyslexic', sans-serif;
                    }
                </style>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to load movie: {str(e)}")
        return
    
    # 3. Hero Section
    if details.backdrop_path:
        st.image(
            f"https://image.tmdb.org/t/p/w1280{details.backdrop_path}",
            use_column_width=True,
            caption=f"{details.title} ({details.release_date[:4]})" if details.release_date else details.title
        )
    
    # 4. Metadata Columns
    col1, col2 = st.columns([1, 3])
    with col1:
        if details.poster_path:
            st.image(
                f"https://image.tmdb.org/t/p/w500{details.poster_path}",
                use_column_width=True
            )
        else:
            st.image(
                "media_assets/icons/poster_placeholder.png",
                use_column_width=True
            )
            
    with col2:
        # Title with year
        release_year = details.release_date[:4] if details.release_date else "N/A"
        st.title(f"{details.title} ({release_year})")
        
        # Rating and runtime
        rating_runtime = []
        if details.vote_average > 0:
            rating_runtime.append(f"⭐ {details.vote_average:.1f}")
        if details.runtime:
            rating_runtime.append(f"🕒 {_format_runtime(details.runtime)}")
        if rating_runtime:
            st.caption(" • ".join(rating_runtime))
        
        # Overview with expandable "Read More"
        with st.expander("Overview", expanded=True):
            st.markdown(details.overview or "*No overview available*")
        
        # Smart Tags
        SmartTagDisplay.render(
            genres=[g.name for g in details.genres],
            directors=[d.name for d in details.directors],
            moods=getattr(details, 'moods', [])  # Optional mood tags
        )
        
        # Watchlist button with state awareness
        if _is_in_watchlist(movie_id):
            if st.button("✓ In Watchlist", help="Already in your watchlist"):
                update_watchlist(movie_id, remove=True)
                st.toast("Removed from watchlist")
        else:
            if st.button("💖 Add to Watchlist"):
                update_watchlist({
                    'id': movie_id,
                    'title': details.title,
                    'poster_path': details.poster_path,
                    'added': datetime.now().isoformat()
                })
                st.toast("Added to watchlist!")
    
    # 5. Interactive Tabs
    tab1, tab2, tab3 = st.tabs(["Cast", "Media", "Details"])
    
    with tab1:
        CastList.display(
            cast=[c for c in details.cast if c.profile_path],
            columns=6,
            max_rows=2
        )
    
    with tab2:
        if videos:
            st.video(f"https://youtube.com/watch?v={videos[0].key}")
        else:
            st.warning("No trailer available")
            
        # Backdrop images gallery
        if getattr(details, 'images', None):
            st.subheader("Gallery")
            cols = st.columns(3)
            for idx, img in enumerate(details.images[:3]):
                cols[idx].image(
                    f"https://image.tmdb.org/t/p/w500{img.file_path}",
                    use_column_width=True
                )
    
    with tab3:
        # Additional metadata
        st.subheader("Production Details")
        if details.production_companies:
            st.markdown("**Studios:** " + ", ".join(
                c.name for c in details.production_companies
            ))
        
        if details.release_date:
            try:
                release_date = datetime.strptime(details.release_date, "%Y-%m-%d")
                st.markdown(f"**Release Date:** {release_date.strftime('%B %d, %Y')}")
            except ValueError:
                st.markdown(f"**Release Year:** {details.release_date[:4]}")
        
        if details.budget > 0:
            st.markdown(f"**Budget:** ${details.budget:,}")
        
        if details.revenue > 0:
            st.markdown(f"**Revenue:** ${details.revenue:,}")