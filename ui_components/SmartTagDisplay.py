import streamlit as st
from typing import List, Optional
from session_utils.state_tracker import get_user_prefs
from session_utils.url_formatting import update_query_params

def render(
    genres: List[str],
    directors: List[str],
    moods: Optional[List[str]] = None,
    max_tags: int = 6
):
    """
    Enhanced with:
    - Mood tag support
    - Better mobile responsiveness
    - User preference awareness
    """
    tags = []
    
    # Apply user preferences
    prefs = get_user_prefs()
    if prefs.cinephile_mode:
        max_tags += 2  # Allow more tags for cinephiles
    
    # Priority: Directors -> Moods -> Genres
    tags.extend([f"🎬 {d}" for d in directors[:1]])
    if moods:
        tags.extend([f"🎭 {m}" for m in moods[:1]])
    tags.extend(genres[:max_tags - len(tags)])
    
    if not tags:
        return
    
    st.write("")  # Spacer
    cols = st.columns(min(4, len(tags)))
    
    for idx, tag in enumerate(tags):
        with cols[idx % len(cols)]:
            if st.button(
                tag,
                key=f"tag_{tag}",
                help=f"Filter by {tag.replace('🎬 ', '').replace('🎭 ', '')}",
                use_container_width=True
            ):
                # Different filter types based on tag prefix
                if tag.startswith("🎬"):
                    update_query_params({"director": tag[2:]})
                elif tag.startswith("🎭"):
                    update_query_params({"mood": tag[2:]})
                else:
                    update_query_params({"genre": tag})