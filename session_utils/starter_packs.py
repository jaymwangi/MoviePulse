import json
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from session_utils.watchlist_manager import add_to_watchlist

def load_starter_packs() -> Dict[str, List[int]]:
    """Load starter packs from JSON file"""
    try:
        with open(Path("static_data/starter_packs.json")) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load starter packs: {str(e)}")
        return {}

def get_movie_previews(movie_ids: List[int]) -> List[Dict]:
    """Fetch basic movie details for preview"""
    from service_clients.tmdb_client import tmdb_client
    previews = []
    
    for movie_id in movie_ids[:4]:  # Only preview first 4 movies
        try:
            details = tmdb_client.get_movie_details(movie_id)
            previews.append({
                "title": details.get("title"),
                "poster_url": f"https://image.tmdb.org/t/p/w200{details.get('poster_path')}" if details.get("poster_path") else None,
                "year": details.get("release_date", "")[:4] if details.get("release_date") else ""
            })
        except Exception as e:
            previews.append({
                "title": f"Movie {movie_id}",
                "poster_url": None,
                "year": ""
            })
    return previews

def add_starter_pack(pack_name: str, movie_ids: List[int]):
    """Add all movies from a starter pack to watchlist"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        for i, movie_id in enumerate(movie_ids):
            status_text.text(f"Adding {pack_name} movies... ({i+1}/{len(movie_ids)})")
            progress_bar.progress((i + 1) / len(movie_ids))
            add_to_watchlist({
                "movie_id": movie_id,
                "added_at": str(datetime.now())
            })
        
        st.session_state.starter_pack_selected = True
        st.success(f"Added {pack_name} pack to your watchlist!")
        st.balloons()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add some movies: {str(e)}")
        st.session_state.starter_pack_selected = True
        st.rerun()

def get_pack_description(pack_name: str) -> str:
    """Return description for each starter pack"""
    descriptions = {
        "Feel Good": "Uplifting stories to brighten your day",
        "Top Action": "Adrenaline-pumping blockbusters",
        "Critic Picks": "Acclaimed masterpieces",
        "Mind Bending": "Thought-provoking sci-fi and thrillers",
        "Romantic": "Heartwarming love stories",
        "Horror": "Chilling tales for brave viewers",
        "Animated": "Family-friendly masterpieces",
        "Oscar Winners": "Award-winning excellence",
        "90s Classics": "Nostalgic favorites",
        "Sci-Fi": "Futuristic visions and space epics"
    }
    return descriptions.get(pack_name, "Curated collection of films")
def show_starter_pack_selector():
    """Display starter pack selection UI with cinematic visuals"""
    # ---- CSS Injection ----
    st.markdown("""
    <style>
        /* Cinematic theme */
        :root {
            --gold: #FFD700;
            --dark-bg: #0f0f12;
            --card-bg: #1a1a24;
        }
        
        .pack-header {
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 300;
            letter-spacing: 1px;
            color: var(--gold);
            position: relative;
            margin-bottom: 1.5rem;
        }
        .pack-header:after {
            content: "";
            display: block;
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, var(--gold), transparent);
            margin-top: 8px;
        }
        
        .pack-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 215, 0, 0.1);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .pack-card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 215, 0, 0.3);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
        }
        
        .movie-preview {
            border-radius: 8px;
            overflow: hidden;
            position: relative;
            aspect-ratio: 2/3;
            transition: all 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .movie-preview:after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 30%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .movie-preview:hover {
            transform: scale(1.05);
            z-index: 10;
        }
        .movie-preview:hover:after {
            opacity: 1;
        }
        .movie-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .movie-title {
            position: absolute;
            bottom: 8px;
            left: 8px;
            color: white;
            font-size: 0.7rem;
            z-index: 2;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .movie-preview:hover .movie-title {
            opacity: 1;
        }
        
        .select-btn {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
            border: none !important;
            color: #111 !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
        }
        .select-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3) !important;
        }
        
        .skip-btn {
            border: 1px solid var(--gold) !important;
            color: var(--gold) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # ---- Header ----
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0.5rem;'>
            <span style='color: #FFD700;'>🎬</span> Your Movie Journey Begins
        </h1>
        <p style='color: #aaa; max-width: 600px; margin: 0 auto;'>
            Select a starter pack to personalize recommendations, or explore freely
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Pack Grid ----
    packs = load_starter_packs()
    for pack_name, movie_ids in packs.items():
        with st.container():
            # Pack header
            st.markdown(f"""
            <div class='pack-header'>
                ✨ {pack_name} <span style='color: #666; font-size: 0.9em;'>{len(movie_ids)} films</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Pack description
            st.caption(get_pack_description(pack_name))
            
            # Movie preview grid
            preview_movies = get_movie_previews(movie_ids)
            cols = st.columns(4)
            
            for idx, movie in enumerate(preview_movies):
                with cols[idx]:
                    st.markdown(f"""
                    <div class='movie-preview'>
                        <img src='{movie.get("poster_url", "media_assets/posters/placeholder.jpg")}'>
                        <div class='movie-title'>
                            {movie.get("title", "Movie")} <br>
                            <small>{movie.get("year", "")}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Select button
            st.button(
                f"Select {pack_name} Pack",
                key=f"select_{pack_name}",
                on_click=lambda pn=pack_name: add_starter_pack(pn),
                type="primary",
                use_container_width=True
            )
            
            st.divider()

    # Skip option
    st.button(
        "⟶ Explore on my own",
        key="skip_starter_pack",
        on_click=lambda: st.session_state.update({"starter_pack_selected": True}),
        type="secondary",
        use_container_width=True
    )