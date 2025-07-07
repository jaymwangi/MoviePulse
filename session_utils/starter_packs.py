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

def show_starter_pack_selector():
    """Display starter pack selection UI"""
    st.markdown("""
    <style>
        .starter-pack-header {
            color: #FFD700;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
        .starter-pack-card {
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            background: rgba(255, 215, 0, 0.05);
            border: 1px solid rgba(255, 215, 0, 0.2);
            transition: all 0.3s ease;
        }
        .starter-pack-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(255, 215, 0, 0.15);
        }
        .pack-button {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            color: #000 !important;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="starter-pack-header">✨ New here? Pick a Starter Pack ✨</div>', unsafe_allow_html=True)
    st.caption("Get instant recommendations by choosing one of our curated collections")
    
    packs = load_starter_packs()
    for pack_name, movie_ids in packs.items():
        with st.container():
            st.markdown(f'<div class="starter-pack-card">', unsafe_allow_html=True)
            cols = st.columns([3, 1])
            with cols[0]:
                st.subheader(pack_name)
                st.caption(f"{len(movie_ids)} handpicked movies")
            with cols[1]:
                if st.button(
                    "Select", 
                    key=f"starter_{pack_name}",
                    type="primary",
                    use_container_width=True,
                    help=f"Add {pack_name} movies to your watchlist"
                ):
                    for movie_id in movie_ids:
                        add_to_watchlist({
                            "movie_id": movie_id,
                            "title": "",  # Will be filled from TMDB
                            "poster_path": "",
                            "added_at": str(datetime.now())
                        })
                    st.session_state.starter_pack_selected = True
                    st.success(f"Added {pack_name} pack to your watchlist!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
