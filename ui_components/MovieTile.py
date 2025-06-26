# moviepulse/ui_components/MovieTile.py
import streamlit as st
from core_config import constants
import os

def MovieTile(movie_data, show_details=True, testid_suffix=""):
    """
    A reusable movie tile component with hover effects, fallback poster handling, and test attributes
    
    Args:
        movie_data (dict/object): Movie data containing:
            - poster_path (str): Relative path to poster image
            - title (str): Movie title
            - release_year (str): Release year (optional)
        show_details (bool): Whether to show title/year below poster
        testid_suffix (str): Optional suffix for test IDs to make them unique
    """
    # Get fallback image path from constants
    FALLBACK_POSTER = os.path.join("media_assets", "icons", "image-fallback.svg")
    
    # Handle both dictionary and object inputs
    def get_movie_attr(data, attr, default=None):
        if hasattr(data, attr):
            return getattr(data, attr)
        elif isinstance(data, dict):
            return data.get(attr, default)
        return default
    
    # Determine poster path
    poster_path = get_movie_attr(movie_data, 'poster_path')
    if not poster_path or not os.path.exists(poster_path):
        poster_path = FALLBACK_POSTER
    
    # Get title and year
    title = get_movie_attr(movie_data, 'title', 'Untitled')
    release_year = get_movie_attr(movie_data, 'release_year')
    
    # Generate unique test IDs
    tile_testid = f"movie-tile-{testid_suffix}" if testid_suffix else "movie-tile"
    title_testid = f"movie-title-{testid_suffix}" if testid_suffix else "movie-title"
    year_testid = f"movie-year-{testid_suffix}" if testid_suffix else "movie-year"
    
    # Tile container with hover effects and test attributes
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
        st.markdown(
            f'<div class="movie-tile" data-testid="{tile_testid}">', 
            unsafe_allow_html=True
        )
        
        st.image(
            poster_path, 
            use_container_width=True, 
            output_format="PNG"
        )
        
        if show_details:
            st.markdown(
                f'<div class="movie-title" data-testid="{title_testid}">{title}</div>',
                unsafe_allow_html=True
            )
            
            if release_year:
                st.markdown(
                    f'<div class="movie-year" data-testid="{year_testid}">{release_year}</div>',
                    unsafe_allow_html=True
                )
        
        st.markdown('</div>', unsafe_allow_html=True)