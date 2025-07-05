import logging
import time
from logging.handlers import RotatingFileHandler
import sys
import os
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from service_clients.tmdb_client import tmdb_client
from ui_components import CastList, RecommendationCard
from session_utils.state_tracker import (
    get_watchlist,
    update_watchlist,
    get_user_prefs
)
from core_config.constants import (
    TMDB_IMAGE_BASE_URL,
    GENRES_FILE,
    MOODS_FILE
)
from streamlit.components.v1 import html
from ai_smart_recommender.recommender_engine.strategy_interfaces.hybrid_model import hybrid_recommender

# ----------------------- CSS LOADING -----------------------
@st.cache_data
def load_css():
    """Cache the CSS file to avoid repeated disk I/O"""
    try:
        with open("media_assets/styles/main.css") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load CSS: {str(e)}", exc_info=True)
        return ""

# ----------------------- LOGGING CONFIG -----------------------
# Set up rotating file handler
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "movie_details.log")

rotating_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,   # 5 MB per file
    backupCount=3,              # keep last 3 rotated files
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        rotating_handler,
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def log_page_view(movie_id: int, success: bool, duration: float):
    """Structured logging for page views"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "movie_id": movie_id,
        "duration_sec": round(duration, 3),
        "status": "success" if success else "failed"
    }
    logger.info(f"PAGE_VIEW: {log_data}")

def log_user_action(action: str, metadata: Dict = None):
    """Log user interactions"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "session_id": st.session_state.get('session_id', 'unknown'),
        "metadata": metadata or {}
    }
    logger.info(f"USER_ACTION: {log_entry}")
# ----------------------- CACHED FUNCTIONS -----------------------
@st.cache_data(ttl=86400, show_spinner="Loading movie details...")
def get_cached_movie_details(movie_id: int):
    """Get movie details with rate limiting protection"""
    time.sleep(0.3)  # rate limiting buffer
    try:
        return tmdb_client.get_movie_details_extended(movie_id)
    except Exception as e:
        logger.error(f"Failed to fetch details for movie {movie_id}: {str(e)}", exc_info=True)
        raise

@st.cache_data(ttl=3600)
def get_cached_movie_videos(movie_id: int):
    """Get movie videos with error handling"""
    try:
        videos = tmdb_client.get_movie_videos(movie_id)
        return [v for v in videos if v.site == "YouTube"]
    except Exception as e:
        logger.warning(f"Failed to fetch videos for movie {movie_id}: {str(e)}", exc_info=True)
        return []

@st.cache_data(ttl=3600, show_spinner="Generating recommendations...")
def get_cached_recommendations(movie_id: int):
    """Get AI-powered recommendations with caching"""
    try:
        return hybrid_recommender.recommend(movie_id, limit=4)
    except Exception as e:
        logger.error(f"Recommendation failed for movie {movie_id}: {str(e)}", exc_info=True)
        return []

# ----------------------- UTILITY FUNCTIONS -----------------------
def _format_runtime(minutes: int) -> str:
    """Convert runtime to HHh MMm format"""
    return f"{minutes//60}h {minutes%60}m" if minutes else "N/A"

def _format_currency(amount: int) -> str:
    """Format currency with M/B units"""
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    return f"${amount:,}" if amount > 0 else "N/A"

def _is_in_watchlist(movie_id: int) -> bool:
    try:
        return any(m.get("id") == movie_id for m in get_watchlist())
    except Exception as e:
        logger.error(f"Watchlist check failed: {str(e)}", exc_info=True)
        return False

# ----------------------- UI COMPONENTS -----------------------
def render_hero_section(details):
    try:
        if details.backdrop_path:
            st.image(
                f"https://image.tmdb.org/t/p/w1280{details.backdrop_path}",
                use_column_width=True,
                caption=f"{details.title} ({details.release_date[:4]})" if details.release_date else details.title,
                alt=f"Backdrop image for {details.title}"
            )
    except Exception as e:
        logger.warning(f"Failed to load backdrop: {str(e)}", exc_info=True)
        st.image("media_assets/backdrop_error.jpg", alt="Error loading backdrop image")

def render_poster(details):
    try:
        if details.poster_path:
            with st.spinner("Loading poster..."):
                st.image(
                    f"https://image.tmdb.org/t/p/w500{details.poster_path}",
                    use_column_width=True,
                    alt=f"Poster for {details.title}"
                )
        else:
            st.image("media_assets/poster_placeholder.png", alt="Default poster placeholder")
    except Exception as e:
        logger.warning(f"Failed to load poster: {str(e)}", exc_info=True)
        st.image("media_assets/poster_error.png", alt="Error loading poster")

def render_title_section(details, movie_id):
    release_year = details.release_date[:4] if details.release_date else "N/A"
    st.title(f"{details.title} ({release_year})")
    
    metadata = []
    if details.vote_average > 0:
        metadata.append(f"⭐ {details.vote_average:.1f}/10")
    if details.runtime:
        metadata.append(f"🕒 {_format_runtime(details.runtime)}")
    if getattr(details, "adult", False):
        metadata.append("🔞 Adult Content")
    if metadata:
        st.caption(" • ".join(metadata))
    
    with st.expander("Overview", expanded=True):
        st.markdown(details.overview or "*No overview available*")
    
    render_watchlist_button(movie_id, details)

def render_watchlist_button(movie_id, details):
    col1, col2 = st.columns([1, 3])
    with col1:
        if _is_in_watchlist(movie_id):
            if st.button("✓ In Watchlist", key=f"wl_remove_{movie_id}"):
                try:
                    update_watchlist(movie_id, remove=True)
                    st.toast("Removed from watchlist")
                    log_user_action("watchlist_remove", {"movie_id": movie_id})
                    st.rerun()
                except Exception as e:
                    st.error("Update failed - try again")
                    logger.error(f"Watchlist removal failed: {str(e)}", exc_info=True)
        else:
            if st.button("💖 Add to Watchlist", key=f"wl_add_{movie_id}"):
                try:
                    update_watchlist({
                        "id": movie_id,
                        "title": details.title,
                        "poster_path": details.poster_path,
                        "backdrop_path": details.backdrop_path,
                        "added": datetime.now().isoformat()
                    })
                    st.toast("Added to watchlist!")
                    log_user_action("watchlist_add", {"movie_id": movie_id})
                    st.rerun()
                except Exception as e:
                    st.error("Update failed - try again")
                    logger.error(f"Watchlist addition failed: {str(e)}", exc_info=True)

def render_video_content(videos, movie_title):
    if not videos:
        st.warning("No official trailers available")
        if st.button("🔍 Search YouTube", key="yt_search"):
            log_user_action("youtube_search", {"query": movie_title})
            html(f"""
            <script>
                window.open("https://youtube.com/results?search_query={movie_title}+trailer");
            </script>
            """)
        return
    st.video(f"https://youtube.com/watch?v={videos[0].key}")
    if len(videos) > 1:
        with st.expander("More Videos"):
            cols = st.columns(2)
            for idx, video in enumerate(videos[1:3]):
                cols[idx % 2].video(f"https://youtube.com/watch?v={video.key}")

def render_production_details(details):
    st.subheader("Production Details")
    if details.production_companies:
        st.markdown(f"**Studios:** {', '.join(c.name for c in details.production_companies[:3])}")
    if details.release_date:
        try:
            release_date = datetime.strptime(details.release_date, "%Y-%m-%d")
            st.markdown(f"**Release Date:** {release_date.strftime('%B %d, %Y')}")
        except ValueError:
            st.markdown(f"**Release Year:** {details.release_date[:4]}")
    st.markdown(f"**Budget:** {_format_currency(details.budget)}")
    st.markdown(f"**Revenue:** {_format_currency(details.revenue)}")
    if hasattr(details, "spoken_languages"):
        st.markdown(f"**Languages:** {', '.join(l.name for l in details.spoken_languages[:3])}")

def render_recommendations(movie_id: int):
    """Enhanced recommendation display using hybrid recommender output"""
    st.subheader("🍿 You May Also Like", divider="rainbow")
    
    with st.spinner("Analyzing cinematic patterns to find perfect matches..."):
        try:
            recommendations = get_cached_recommendations(movie_id)
            
            if not recommendations:
                st.info("No recommendations found. Try exploring similar genres.")
                return
            
            # Dynamic column layout (2-4 columns based on screen width)
            screen_width = st.session_state.get('screen_width', 1024)
            col_count = 4 if screen_width > 1200 else 3 if screen_width > 800 else 2
            cols = st.columns(col_count, gap="medium")
            
            for idx, rec in enumerate(recommendations[:col_count]):
                with cols[idx % col_count]:
                    # Build detailed explanation from recommendation metadata
                    explanation_parts = []
                    
                    # Add match type context
                    match_type_map = {
                        'vector': "Similar themes and content",
                        'genre': f"Shared genres: {', '.join(rec.genres[:3])}",
                        'mood': "Matches your current mood",
                        'actor': f"Features actors like {', '.join(rec.actors[:2])}",
                        'fallback': "Popular with similar viewers"
                    }
                    explanation_parts.append(match_type_map.get(rec.match_type, rec.match_type))
                    
                    # Add similarity score if available
                    if hasattr(rec, 'similarity_score'):
                        explanation_parts.append(f"Match strength: {rec.similarity_score:.0%}")
                    
                    # Extract poster path from URL if available
                    poster_path = (rec.poster_url.replace(TMDB_IMAGE_BASE_URL, "") 
                                 if rec.poster_url and TMDB_IMAGE_BASE_URL in rec.poster_url 
                                 else None)
                    
                    # Use the RecommendationCard component
                    RecommendationCard(
                        movie={
                            'id': rec.movie_id,
                            'title': rec.title,
                            'poster_path': poster_path,
                            'release_date': '',
                            'vote_average': 0,
                            'genres': rec.genres
                        },
                        explanation="\n".join(explanation_parts),
                        show_explanation=False,
                        card_width=300 if col_count >= 3 else 400
                    )
            
            # Footer with refresh option
            st.caption(f"Showing {len(recommendations[:col_count])} AI-curated recommendations")
            if st.button("🔄 Refresh Recommendations", key="refresh_recs"):
                st.cache_data.clear()
                st.rerun()
            
        except Exception as e:
            logger.error(f"Recommendation render failed: {str(e)}", exc_info=True)
            st.error("Our cinematic matchmaker needs a quick break ☕")
            if st.button("🔄 Try Again", key="retry_recs"):
                st.cache_data.clear()
                st.rerun()

# ----------------------- MAIN PAGE -----------------------
def render_movie_details():
    # Load and inject CSS
    st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)
    
    # Detect screen width (simplified approach)
    if 'screen_width' not in st.session_state:
        try:
            # This is a placeholder - you may need a JS solution for actual width detection
            st.session_state.screen_width = 1024  # Default desktop size
        except:
            st.session_state.screen_width = 768  # Fallback to mobile
            
    view_start = time.perf_counter()
    movie_id = st.query_params.get("id", "")
    try:
        if not movie_id or not movie_id.isdigit():
            raise ValueError("Invalid movie selection")
        movie_id = int(movie_id)
        log_user_action("page_entered", {"movie_id": movie_id})
        
        with st.spinner("Loading cinematic details..."):
            details = get_cached_movie_details(movie_id)
            videos = get_cached_movie_videos(movie_id)
            if not details or not hasattr(details, "title"):
                raise RuntimeError("Incomplete movie data received")
            prefs = get_user_prefs()
            if prefs.dyslexia_font:
                st.markdown("""
                <style>
                    * { font-family: 'OpenDyslexic', sans-serif; }
                </style>
                """, unsafe_allow_html=True)
        
        render_hero_section(details)
        col1, col2 = st.columns([1, 3])
        with col1:
            render_poster(details)
        with col2:
            render_title_section(details, movie_id)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Cast", "Media", "Details", "Recommendations"])
        with tab1:
            CastList.display(
                cast=[c for c in details.cast if c.profile_path],
                columns=6,
                max_rows=2
            )
        with tab2:
            render_video_content(videos, details.title)
            if getattr(details, "images", None):
                st.subheader("Gallery")
                cols = st.columns(3)
                for idx, img in enumerate(details.images[:3]):
                    cols[idx].image(
                        f"https://image.tmdb.org/t/p/w500{img.file_path}",
                        use_column_width=True,
                        alt=f"Gallery image {idx+1} for {details.title}"
                    )
        with tab3:
            render_production_details(details)
        with tab4:
            render_recommendations(movie_id)
        
        st.button("← Back to Home", on_click=lambda: st.session_state.update({"current_page": "home"}))
        log_page_view(movie_id, True, time.perf_counter() - view_start)
        
    except ValueError as e:
        st.error(str(e))
        st.page_link("pages/Home.py", label="← Back to Home")
        log_page_view(movie_id, False, time.perf_counter() - view_start)
    except Exception as e:
        logger.error(f"Page render failed: {str(e)}", exc_info=True)
        st.error("A technical error occurred")
        if st.button("Retry"):
            st.rerun()
        log_page_view(movie_id, False, time.perf_counter() - view_start)

# ----------------------- EXECUTION -----------------------
if __name__ == "__main__":
    st.set_page_config(
        page_title="Movie Details",
        page_icon="🎬",
        layout="wide"
    )
    
    # Add screen width detection
    js = """
    <script>
    function reportWindowSize() {
        window.parent.postMessage({
            type: 'screenWidth',
            width: window.innerWidth
        }, '*');
    }
    window.addEventListener('resize', reportWindowSize);
    reportWindowSize();
    </script>
    """
    st.components.v1.html(js)
    

# expose the page handler for imports
movie_details_page = render_movie_details