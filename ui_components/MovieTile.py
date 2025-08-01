import streamlit as st
from typing import Union, Optional
from pathlib import Path

def MovieTile(
    movie_data: Union[dict, object],
    testid_suffix: Optional[str] = None,
    lazy_load: bool = True,
    debug: bool = False,
    **kwargs
):
    """
    Theme-Aware Movie Tile Component v7.1
    
    Features:
    - Automatically adapts to Streamlit light/dark theme
    - Consistent metadata layout with perfect grid alignment
    - Theme-appropriate colors for all elements
    - Preserves all hover effects and interactions
    """

    # ===== DATA VALIDATION & EXTRACTION ===== 
    # (Keep the same data extraction logic as before)
    if not movie_data:
        if debug:
            st.error("No movie data provided")
        return

    if not isinstance(movie_data, dict):
        try:
            movie_data = vars(movie_data)
        except TypeError:
            if debug:
                st.error("Invalid movie data format")
            return

    if debug:
        st.json(movie_data)

    title = str(movie_data.get('title', 'Untitled')).strip()
    release_date = str(movie_data.get('release_date', ''))
    release_year = release_date[:4] if release_date and len(release_date) >= 4 else 'N/A'

    try:
        rating = float(movie_data.get('vote_average', 0))
        rating_str = f"⭐ {rating:.1f}" if rating > 0 else "⭐ N/A"
    except (TypeError, ValueError):
        rating_str = "⭐ N/A"

    runtime_str = "⏱ N/A"
    runtime = None
    if 'runtime' in movie_data:
        runtime = movie_data['runtime']
    elif 'details' in movie_data and 'runtime' in movie_data['details']:
        runtime = movie_data['details']['runtime']
    
    if runtime:
        try:
            mins = int(runtime)
            if mins > 0:
                hours, mins = divmod(mins, 60)
                runtime_str = f"⏱ {hours}h {mins:02d}m" if hours else f"⏱ {mins}m"
        except (TypeError, ValueError):
            if debug:
                st.warning(f"Invalid runtime: {runtime}")

    overview = str(movie_data.get('overview', ''))[:120] + "..." if movie_data.get('overview') else "No description available"

    genre_tags = ["No genres"]
    genres = []
    
    if 'genres' in movie_data:
        genres = movie_data['genres']
    elif 'details' in movie_data and 'genres' in movie_data['details']:
        genres = movie_data['details']['genres']
    
    if genres:
        if isinstance(genres, list):
            if genres and isinstance(genres[0], dict):
                genre_tags = [g['name'] for g in genres if g.get('name')]
            elif genres and hasattr(genres[0], 'name'):
                genre_tags = [g.name for g in genres if g.name]
            else:
                genre_tags = [str(g) for g in genres]
    
    genre_tags = [g.strip() for g in genre_tags[:3] if g and str(g).strip()] or ["No genres"]

    poster_path = str(movie_data.get('poster_path', ''))
    if not poster_path:
        image_url = "media_assets/icons/person_placeholder.png"
    elif poster_path.startswith(('http://', 'https://')):
        image_url = poster_path
    elif Path(poster_path).exists():
        image_url = str(Path(poster_path).resolve())
    else:
        image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"

    # ===== THEME-AWARE STYLING =====
    # Detect current theme
    try:
        theme = st._config.get_option("theme.base") or "light"
    except:
        theme = "light"

    is_dark = theme == "dark"

    # Theme-specific colors
    bg_color = "rgba(10, 10, 10, 0.9)" if is_dark else "rgba(255, 255, 255, 0.9)"
    text_color = "#FFFFFF" if is_dark else "#333333"
    meta_color = "#BBBBBB" if is_dark else "#666666"
    genre_bg = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.05)"
    genre_text = "#EEEEEE" if is_dark else "#555555"
    hover_bg = "rgba(0, 0, 0, 0.7)" if is_dark else "rgba(0, 0, 0, 0.6)"
    shadow_color = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.1)"

    css = f"""
    <style>
    [data-testid="movie-tile-{testid_suffix if testid_suffix else 'default'}"] {{
        width: 100%;
        margin-bottom: 1rem;
        position: relative;
    }}
    
    /* Poster container */
    .movie-poster-container {{
        position: relative;
        aspect-ratio: 2/3;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 8px;
        transition: transform 0.3s ease;
        box-shadow: 0 2px 8px {shadow_color};
    }}
    
    .movie-poster-container:hover {{
        transform: scale(1.05);
        box-shadow: 0 4px 12px {shadow_color};
    }}
    
    .movie-poster {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    
    /* Overlay elements */
    .movie-poster-overlay {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: {hover_bg};
        opacity: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: opacity 0.3s ease;
        padding: 16px;
    }}
    
    .movie-poster-container:hover .movie-poster-overlay {{
        opacity: 1;
    }}
    
    .action-buttons {{
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
    }}
    
    .action-button {{
        background: {bg_color};
        border: none;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s ease, background 0.2s ease;
        color: {text_color};
    }}
    
    .action-button:hover {{
        transform: scale(1.1);
        background: {'rgba(255, 255, 255, 0.95)' if is_dark else 'rgba(255, 255, 255, 1)'};
    }}
    
    /* Hover info panel */
    .hover-info-panel {{
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 12px;
        transform: translateY(100%);
        transition: transform 0.3s ease;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
    }}
    
    .movie-poster-container:hover .hover-info-panel {{
        transform: translateY(0);
    }}
    
    .hover-title {{
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    
    .hover-meta {{
        font-size: 0.85rem;
        margin-bottom: 8px;
        display: flex;
        gap: 8px;
        opacity: 0.9;
    }}
    
    .hover-overview {{
        font-size: 0.8rem;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    /* Metadata section - theme aware */
    .movie-info {{
        padding: 8px 4px 0;
        display: flex;
        flex-direction: column;
        min-height: 110px;
    }}
    
    .movie-title {{
        font-weight: 600;
        font-size: 1rem;
        line-height: 1.3;
        margin: 0 0 6px 0;
        color: {text_color};
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    .movie-meta {{
        display: flex;
        gap: 8px;
        font-size: 0.85rem;
        margin: 0 0 8px 0;
        flex-wrap: wrap;
        align-items: center;
        color: {meta_color};
    }}
    
    .movie-meta span {{
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }}
    
    /* Genre tags */
    .movie-genres {{
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: auto;
    }}
    
    .genre-tag {{
        background: {genre_bg};
        color: {genre_text};
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        line-height: 1;
        white-space: nowrap;
    }}
    
    .genre-tag.no-genres {{
        opacity: 0.7;
        font-style: italic;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # ===== RENDERING =====
    with st.container():
        # Poster Container with Hover Effects
        st.markdown(
            f"""<div class="movie-poster-container" 
                 data-testid="poster-{testid_suffix if testid_suffix else 'default'}">
                <img class="movie-poster" 
                     src="{image_url}" 
                     alt="{title}" 
                     loading="{'lazy' if lazy_load else 'eager'}"
                     onerror="this.src='media_assets/icons/person_placeholder.png'">
                
                <div class="movie-poster-overlay">
                    <div class="action-buttons">
                        <button class="action-button">❤️</button>
                        <button class="action-button">➕</button>
                    </div>
                </div>
                
                <div class="hover-info-panel">
                    <div class="hover-title">{title}</div>
                    <div class="hover-meta">
                        {release_year} • {rating_str.replace('⭐ ', '⭐')} • {runtime_str.replace('⏱ ', '')}
                    </div>
                    <div class="hover-overview">{overview}</div>
                </div>
            </div>""",
            unsafe_allow_html=True
        )

        # Always-visible Info Section
        st.markdown(
            f'<div class="movie-info">'
            f'<div class="movie-title" title="{title}">{title}</div>'
            f'<div class="movie-meta">'
            f'<span>🗓 {release_year}</span>'
            f'<span>{rating_str}</span>'
            f'<span>{runtime_str}</span>'
            f'</div>'
            f'<div class="movie-genres">{"".join([f"<span class=\'genre-tag{" no-genres" if g == "No genres" else ""}\'>{g}</span>" for g in genre_tags])}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# Test cases with theme toggle
if __name__ == "__main__":
    st.title("Movie Tile Component Test - Theme Aware")
    
    # Add theme toggle for testing
    if st.toggle("Dark Theme", False):
        st._config.set_option("theme.base", "dark")
    else:
        st._config.set_option("theme.base", "light")
    
    test_movies = [
        {
            "title": "Inception",
            "release_date": "2010-07-16",
            "vote_average": 8.4,
            "runtime": 148,
            "genres": [{"name": "Action"}, {"name": "Sci-Fi"}, {"name": "Mystery"}],
            "poster_path": "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg",
            "overview": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
            "id": 123
        },
        {
            "title": "The Dark Knight",
            "release_date": "2008-07-16",
            "vote_average": 9.0,
            "runtime": 152,
            "genres": [{"name": "Action"}, {"name": "Crime"}, {"name": "Drama"}],
            "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
            "overview": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
            "id": 155
        },
        {
            "title": "Movie Missing Data",
            "release_date": "",
            "vote_average": 0,
            "runtime": None,
            "genres": [],
            "poster_path": "",
            "overview": "",
            "id": 456
        }
    ]
    
    cols = st.columns(3)
    for idx, movie in enumerate(test_movies):
        with cols[idx % 3]:
            MovieTile(
                movie,
                testid_suffix=f"test_{idx}",
                debug=True
            )