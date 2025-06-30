# ui_components/MovieTile.py
import streamlit as st
from core_config import constants
import os
from session_utils.url_formatting import update_query_params

def MovieTile(movie_data, show_details=True, testid_suffix=""):
    """
    A reusable movie tile component with hover effects, click behavior, and test attributes
    
    Args:
        movie_data (dict/object): Movie data containing:
            - id (int): TMDB movie ID
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
    
    # Extract movie attributes
    movie_id = get_movie_attr(movie_data, 'id')
    poster_path = get_movie_attr(movie_data, 'poster_path')
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
            cursor: pointer;
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
    
    # Create clickable container
    with st.container():
        # Use columns to make entire area clickable
        col = st.columns(1)[0]
        with col:
            # Create a unique key for each movie
            tile_key = f"movie_tile_{movie_id}_{testid_suffix}"
            
            # Display the movie content
            st.markdown(
                f'<div class="movie-tile" data-testid="{tile_testid}">', 
                unsafe_allow_html=True
            )
            
            # Use empty container as click target
            clicked = st.empty()
            
            # Display poster image
            poster_url = (f"https://image.tmdb.org/t/p/w500{poster_path}" 
                          if poster_path and not poster_path.startswith("media_assets") 
                          else poster_path or FALLBACK_POSTER)
            
            clicked.image(
                poster_url,
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
            
            # Add invisible button overlay for click handling
            if st.button(" ", key=f"invisible_btn_{tile_key}", 
                        help=f"View details for {title}",
                        use_container_width=True):
                update_query_params({"id": str(movie_id)})
                st.switch_page("pages/3_🎬_MovieDetails.py")