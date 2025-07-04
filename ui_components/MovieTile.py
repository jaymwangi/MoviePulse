"""
Enhanced Movie Tile Component with Progressive Image Loading
----------------------------------------------------------
Features:
- Low-res placeholder that swaps to high-res on hover/click
- Graceful fallback to placeholder image
- Optimized loading states
- Accessibility improvements
"""

import streamlit as st
import os
import time  # <-- ADDED for timing
from typing import Optional, Union
from core_config.constants import Movie
from session_utils.url_formatting import update_query_params

# Constants
FALLBACK_POSTER = os.path.join("media_assets", "icons", "person_placeholder.png")
PLACEHOLDER_QUALITY = "w92"  # TMDB's lowest quality
HIGH_QUALITY = "w500"        # TMDB's medium quality

def MovieTile(
    movie_data: Union[Movie, dict],
    show_details: bool = True,
    testid_suffix: str = "",
    lazy_load: bool = True
):
    """
    Enhanced movie tile with progressive image loading.
    
    Args:
        movie_data: Movie data (object or dict)
        show_details: Show title/year below poster
        testid_suffix: Unique identifier for testing
        lazy_load: Enable progressive image loading
    """
    # Start timing the entire component render
    render_start = time.time()
    
    # Extract movie attributes
    movie_id = getattr(movie_data, 'id', None) or movie_data.get('id')
    title = getattr(movie_data, 'title', None) or movie_data.get('title', 'Untitled')
    release_year = (getattr(movie_data, 'release_date', None) or 
                   movie_data.get('release_date', ''))[:4]
    poster_path = getattr(movie_data, 'poster_path', None) or movie_data.get('poster_path')

    # Generate image URLs
    url_start = time.time()
    low_res_url = (f"https://image.tmdb.org/t/p/{PLACEHOLDER_QUALITY}{poster_path}" 
                  if poster_path else FALLBACK_POSTER)
    high_res_url = (f"https://image.tmdb.org/t/p/{HIGH_QUALITY}{poster_path}" 
                   if poster_path else FALLBACK_POSTER)
    url_elapsed = time.time() - url_start
    st.session_state.setdefault('perf_log', []).append(
        f"MovieTile URL generation took {url_elapsed:.4f}s"
    )

    # CSS for hover effects and transitions
    css_start = time.time()
    st.markdown(f"""
    <style>
        /* ... (your existing CSS remains exactly the same) ... */
    </style>
    """, unsafe_allow_html=True)
    css_elapsed = time.time() - css_start
    st.session_state.setdefault('perf_log', []).append(
        f"MovieTile CSS processing took {css_elapsed:.4f}s"
    )

    # Tile container
    with st.container():
        col = st.columns(1)[0]
        with col:
            # Main tile structure
            tile_start = time.time()
            st.markdown(
                f'<div class="movie-tile" data-testid="movie-tile-{testid_suffix}">',
                unsafe_allow_html=True
            )
            
            # Image container with both quality versions
            img_start = time.time()
            st.markdown(
                f'<div class="poster-container" style="position: relative;">'
                f'<img class="movie-poster" src="{low_res_url}" alt="{title} poster">'
                f'<img class="movie-poster high-res" src="{high_res_url}" alt="{title} high-res poster"'
                f' loading="{ "lazy" if lazy_load else "eager" }">'
                f'</div>',
                unsafe_allow_html=True
            )
            img_elapsed = time.time() - img_start
            st.session_state.setdefault('perf_log', []).append(
                f"MovieTile image rendering took {img_elapsed:.4f}s"
            )
            
            # Movie details
            if show_details:
                details_start = time.time()
                st.markdown(
                    f'<div class="movie-title" data-testid="movie-title-{testid_suffix}">{title}</div>',
                    unsafe_allow_html=True
                )
                if release_year:
                    st.markdown(
                        f'<div class="movie-year" data-testid="movie-year-{testid_suffix}">{release_year}</div>',
                        unsafe_allow_html=True
                    )
                details_elapsed = time.time() - details_start
                st.session_state.setdefault('perf_log', []).append(
                    f"MovieTile details rendering took {details_elapsed:.4f}s"
                )
            
            # Clickable overlay
            st.markdown(
                f'<div class="click-overlay" onclick="window.location.href=\'?id={movie_id}\'"></div>',
                unsafe_allow_html=True
            )
            
            st.markdown('</div>', unsafe_allow_html=True)

            # Handle click via invisible button (fallback for Streamlit)
            if st.button(" ", key=f"movie_tile_{movie_id}_{testid_suffix}",
                        help=f"View {title} details",
                        use_container_width=True):
                update_query_params({"id": str(movie_id)})
                st.rerun()

    # Log total render time
    render_elapsed = time.time() - render_start
    st.session_state.setdefault('perf_log', []).append(
        f"MovieTile TOTAL render took {render_elapsed:.4f}s"
    )