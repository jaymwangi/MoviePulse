# -*- coding: utf-8 -*-

import streamlit as st
from datetime import datetime
from pathlib import Path
import json
from ai_smart_recommender.user_personalization import (
    WatchHistory,
    GenreAffinityModel
)

def show():
    st.title("🎭 Your Profile")  # Fixed emoji
    
    if "user_id" not in st.session_state:
        st.warning("Please sign in to view preferences")
        return
    
    user_id = st.session_state.user_id
    history = WatchHistory()
    affinity = GenreAffinityModel()
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Top Genres")
        pref_vector = affinity.build_preference_vector(user_id)
        
        if pref_vector:
            top_genres = sorted(
                pref_vector.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for genre, score in top_genres:
                st.progress(
                    score,
                    text=f"{genre.title()} ({score:.0%})"
                )
        else:
            st.info("No genre preferences yet. Watch more movies!")

    with col2:
        st.header("Recently Watched")
        recent = history.get_user_history(user_id, limit=5)
        
        if recent:
            for entry in recent:
                dt = datetime.fromisoformat(entry["timestamp"])
                st.markdown(
                    f"**{dt.strftime('%b %d')}** · "
                    f"Movie ID: {entry['movie_id']} "
                    f"({', '.join(entry['genres'])})"
                )
        else:
            st.info("No viewing history yet")

    # Downloadable data section
    st.divider()
    with st.expander("📥 Export Your Data"):  # Fixed emoji
        st.download_button(
            label="Download genre preferences",
            data=json.dumps(pref_vector, indent=2),
            file_name=f"moviepulse_prefs_{user_id}.json",
            mime="application/json"
        )
