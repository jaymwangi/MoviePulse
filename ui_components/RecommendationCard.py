"""
Enhanced Recommendation Card with AI Explanations
-----------------------------------------------
Features:
- Critic-mode specific styling (Arthouse/Blockbuster)
- Multi-source recommendation explanations
- Performance metrics display
- Watchlist integration
- Responsive layout
"""

import streamlit as st
from typing import Union, Optional
from dataclasses import dataclass

from service_clients.tmdb_client import tmdb_client
from session_utils.performance_monitor import log_performance
from core_config.constants import Movie
from ai_smart_recommender.recommender_engine.strategy_interfaces.hybrid_model import MovieRecommendation

# Critic mode styling presets
CRITIC_STYLES = {
    "arthouse_snob": {
        "color": "#6BFF6B",  # Muted green
        "border": "2px solid #6BFF6B",
        "badge": "🎨",
        "bg": "rgba(107, 255, 107, 0.05)",
        "reason_icon": "🤔"
    },
    "blockbuster_fan": {
        "color": "#FF6B6B",  # Vibrant red
        "border": "2px solid #FF6B6B",
        "badge": "🍿",
        "bg": "rgba(255, 107, 107, 0.05)",
        "reason_icon": "💥"
    },
    "default": {
        "color": "#888",
        "border": "1px solid #444",
        "badge": "🎥",
        "bg": "rgba(136, 136, 136, 0.05)",
        "reason_icon": "✨"
    }
}

# Recommendation type styling
REC_TYPE_STYLES = {
    'vector': {'icon': '🧠', 'color': '#4e79a7'},
    'genre': {'icon': '🎭', 'color': '#59a14f'},
    'mood': {'icon': '🌧️', 'color': '#edc948'},
    'actor': {'icon': '👨‍🎤', 'color': '#e15759'},
    'fallback': {'icon': '🔄', 'color': '#b07aa1'},
    'popular': {'icon': '🔥', 'color': '#76b7b2'}
}

@dataclass
class RecommendationDisplayConfig:
    show_explanation: bool = True
    show_metrics: bool = False
    compact_mode: bool = False

def _get_style_config():
    mode = st.session_state.get("critic_mode", "default").lower()
    return CRITIC_STYLES.get(mode, CRITIC_STYLES["default"])

def _get_recommendation_style(match_type: Optional[str]):
    return REC_TYPE_STYLES.get(match_type, REC_TYPE_STYLES['popular'])

def RecommendationCard(
    movie: Union[dict, Movie, MovieRecommendation],
    config: Optional[RecommendationDisplayConfig] = None
):
    if config is None:
        config = RecommendationDisplayConfig()

    timer = log_performance("RecommendationCard")
    style = _get_style_config()

    # Extract core movie data
    with timer.child("Data Extraction"):
        movie_id = getattr(movie, 'id', movie.get('id'))
        title = getattr(movie, 'title', movie.get('title', 'Untitled'))
        poster_path = getattr(movie, 'poster_path', movie.get('poster_path'))
        vote_avg = getattr(movie, 'vote_average', movie.get('vote_average', 0))
        release_date = getattr(movie, 'release_date', movie.get('release_date'))

        genres = []
        if hasattr(movie, 'genres'):
            genres = [g.name if hasattr(g, 'name') else str(g) for g in movie.genres]
        else:
            genres = movie.get('genres', [])

    # Extract recommendation-specific data
    with timer.child("Rec Data Extraction"):
        is_recommendation = hasattr(movie, 'match_type')
        match_type = getattr(movie, 'match_type', None)
        reason = getattr(movie, 'reason_label', None) or getattr(movie, 'explanation', None)
        similarity = getattr(movie, 'similarity_score', None)
        rec_style = _get_recommendation_style(match_type)

    # CSS Injection
    with timer.child("CSS Generation"):
        st.markdown(f"""
        <style>
            .rec-card-{movie_id} {{
                border: {style['border']} !important;
                border-radius: 8px !important;
                background: {style['bg']} !important;
                padding: 12px !important;
                margin-bottom: 16px !important;
                position: relative !important;
            }}
            .rec-badge {{
                position: absolute !important;
                top: 8px !important;
                right: 8px !important;
                font-size: 1.2em !important;
                color: {rec_style['color']} !important;
            }}
            .rec-reason {{
                font-size: 0.85rem !important;
                color: {style['color']} !important;
                padding: 8px 0 !important;
                border-top: 1px dashed {style['color']} !important;
                margin-top: 8px !important;
            }}
        </style>
        """, unsafe_allow_html=True)

    # Card layout
    with st.container():
        with st.container(border=True, className=f"rec-card-{movie_id}"):
            if is_recommendation:
                st.markdown(
                    f'<div class="rec-badge" title="{match_type} recommendation">'
                    f'{rec_style["icon"]}</div>',
                    unsafe_allow_html=True
                )

            col1, col2 = st.columns([1, 3])
            with col1:
                poster_url = tmdb_client._get_poster_url(poster_path, 'w154') if poster_path else None
                st.image(
                    poster_url or "media_assets/icons/image-fallback.svg",
                    width=120,
                    use_column_width=True
                )

            with col2:
                st.markdown(
                    f"<span style='color: {style['color']}; font-weight: bold;'>{title}</span>",
                    unsafe_allow_html=True
                )

                meta_cols = st.columns(3)
                with meta_cols[0]:
                    if release_date:
                        st.caption(f"📅 {release_date[:4]}")
                with meta_cols[1]:
                    if genres:
                        st.caption(f"🎭 {', '.join(genres[:2])}")
                with meta_cols[2]:
                    if vote_avg > 0:
                        st.caption(f"⭐ {vote_avg:.1f}")

                if similarity is not None:
                    st.progress(
                        min(float(similarity), 1.0),
                        text=f"Match: {similarity:.0%}"
                    )

                if reason and config.show_explanation:
                    st.markdown(
                        f'<div class="rec-reason">'
                        f'{style["reason_icon"]} {reason}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                btn_cols = st.columns([2, 1, 1])
                with btn_cols[0]:
                    if st.button(
                        "View Details",
                        key=f"view_{movie_id}",
                        use_container_width=True
                    ):
                        st.session_state['selected_movie'] = movie_id
                        st.rerun()

                with btn_cols[1]:
                    if st.button(
                        "❤️ Save",
                        key=f"save_{movie_id}",
                        use_container_width=True
                    ):
                        st.session_state.setdefault('saved_movies', []).append(movie_id)
                        st.toast(f"Saved {title}")

                with btn_cols[2]:
                    if st.button(
                        "🚫 Hide",
                        key=f"hide_{movie_id}",
                        use_container_width=True
                    ):
                        st.session_state.setdefault('hidden_movies', []).append(movie_id)
                        st.rerun()

    timer.stop()
