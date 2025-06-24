# moviepulse/ui_components/MovieTile.py
import streamlit as st
from core_config import constants
import os

def MovieTile(movie_data, show_details=True):
    """
    A reusable movie tile component with hover effects and fallback poster handling
    
    Args:
        movie_data (dict): Movie data containing at least:
            - 'poster_path' (str): Relative path to poster image
            - 'title' (str): Movie title
            - 'release_year' (str): Release year (optional)
        show_details (bool): Whether to show title/year below poster
    """
    # Get fallback image path from constants
    FALLBACK_POSTER = os.path.join("media_assets", "icons", "image-fallback.svg")
    
    # Determine poster path
    poster_path = movie_data.get('poster_path')
    if not poster_path or not os.path.exists(poster_path):
        poster_path = FALLBACK_POSTER
    
    # Tile container with hover effects
    st.markdown(f"""
    <style>
        .movie-tile {{
            transition: transform 0.2s, box-shadow 0.2s;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 16px;
        }}
        .movie-tile:hover {{
            transform: scale(1.05);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        .movie-poster {{
            width: 100%;
            height: auto;
            aspect-ratio: 2/3;
            object-fit: cover;
        }}
        .movie-title {{
            font-weight: bold;
            margin-top: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .movie-year {{
            color: #666;
            font-size: 0.8em;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f'<div class="movie-tile">', unsafe_allow_html=True)
        
        # Display poster image
        st.image(poster_path, use_column_width=True, output_format="PNG")
        
        if show_details:
            # Display title and year
            st.markdown(f'<div class="movie-title">{movie_data["title"]}</div>', unsafe_allow_html=True)
            if movie_data.get('release_year'):
                st.markdown(f'<div class="movie-year">{movie_data["release_year"]}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)