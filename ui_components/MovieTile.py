
import streamlit as st
import streamlit.components.v1 as components
from typing import Union, Optional
from pathlib import Path
import json

def MovieTile(
    movie_data: Union[dict, object],
    testid_suffix: Optional[str] = None,
    lazy_load: bool = True,
    debug: bool = False,
    **kwargs
):
    """
    Movie Tile Component v9.2 - Fully Fixed Version
    - Working toasts on like/add
    - Reversible buttons
    - Theme-aware metadata
    - Perfect grid alignment
    """
    
    # ===== DATA EXTRACTION =====
    if not movie_data:
        if debug:
            st.error("No movie data provided")
        return None

    if not isinstance(movie_data, dict):
        try:
            movie_data = vars(movie_data)
        except TypeError:
            if debug:
                st.error("Invalid movie data format")
            return None

    # Extract data with fallbacks
    title = str(movie_data.get('title', 'Untitled')).strip()
    release_date = str(movie_data.get('release_date', ''))
    release_year = release_date[:4] if release_date and len(release_date) >= 4 else 'N/A'
    
    try:
        rating = float(movie_data.get('vote_average', 0))
        rating_str = f"{rating:.1f}" if rating > 0 else 'N/A'
    except (TypeError, ValueError):
        rating_str = "N/A"

    runtime_str = "N/A"
    runtime = movie_data.get('runtime') or movie_data.get('details', {}).get('runtime')
    if runtime:
        try:
            mins = int(runtime)
            if mins > 0:
                hours, mins = divmod(mins, 60)
                runtime_str = f"{hours}h {mins:02d}m" if hours else f"{mins}m"
        except (TypeError, ValueError):
            if debug:
                st.warning(f"Invalid runtime: {runtime}")

    overview = str(movie_data.get('overview', ''))[:300] + ("..." if len(str(movie_data.get('overview', ''))) > 300 else "") if movie_data.get('overview') else "No description available"

    genres = movie_data.get('genres') or movie_data.get('details', {}).get('genres', [])
    genre_tags = (
        [g['name'] for g in genres if isinstance(g, dict) and g.get('name')] or
        [g.name for g in genres if hasattr(g, 'name')] or
        [str(g) for g in genres if g]
    )[:3] or ["No genres"]

    poster_path = str(movie_data.get('poster_path', ''))
    if not poster_path:
        image_url = "https://via.placeholder.com/300x450?text=No+Poster"
    elif poster_path.startswith(('http://', 'https://')):
        image_url = poster_path
    elif Path(poster_path).exists():
        image_url = str(Path(poster_path).resolve())
    else:
        image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"

    # ===== STATE MANAGEMENT =====
    tile_key = f"{testid_suffix or 'default'}_{title.replace(' ', '_')}"
    liked_key = f"{tile_key}_liked"
    watchlist_key = f"{tile_key}_watchlisted"
    
    # Initialize state if not exists
    if liked_key not in st.session_state:
        st.session_state[liked_key] = False
    if watchlist_key not in st.session_state:
        st.session_state[watchlist_key] = False

    # ===== THEME DETECTION =====
    try:
        theme = st._config.get_option("theme.base") or "light"
        is_dark = theme == "dark"
    except:
        is_dark = False

    # ===== COMPONENT MARKUP =====
    html_content = f"""
    <style>
    /* Container - Ensures consistent sizing */
    .movie-tile-{tile_key} {{
        position: relative;
        width: 100%;
        aspect-ratio: 2/3;
        margin-bottom: 1rem;
        border-radius: 8px;
        overflow: hidden;
        transition: transform 0.3s ease;
    }}
    
    .movie-tile-{tile_key}:hover {{
        transform: scale(1.03);
        z-index: 10;
    }}
    
    /* Poster Image - Strict aspect ratio */
    .movie-poster-{tile_key} {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    
    /* Action Buttons - Centered */
    .action-buttons-{tile_key} {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        gap: 16px;
        z-index: 2;
        opacity: 0;
        transition: opacity 0.3s ease;
    }}
    
    .movie-tile-{tile_key}:hover .action-buttons-{tile_key} {{
        opacity: 1;
    }}
    
    .action-button-{tile_key} {{
        background: rgba(255, 255, 255, 0.9);
        border: none;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 1.1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}
    
    .action-button-{tile_key}:hover {{
        background: #ffdede;
        transform: scale(1.1);
    }}
    
    .action-button-{tile_key}.liked {{
        color: #ff4d4d;
        background: #ffe6e6;
    }}
    
    .action-button-{tile_key}.added {{
        color: #4dff4d;
        background: #e6ffe6;
    }}
    
    /* Hover Panel - 1/8 height by default */
    .hover-panel-{tile_key} {{
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 12.5%;
        background: rgba(0, 0, 0, 0.85);
        color: #ffffff;
        padding: 8px 12px;
        transition: height 0.3s ease;
        z-index: 3;
        overflow: hidden;
        cursor: pointer;
        backdrop-filter: blur(2px);
    }}
    
    /* Expanded State - Full height */
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
        height: 100%;
        overflow-y: auto;
        backdrop-filter: blur(4px);
    }}
    
    /* Hide buttons when expanded */
    .movie-tile-{tile_key}.expanded .action-buttons-{tile_key} {{
        display: none;
    }}
    
    /* Panel Content */
    .hover-title-{tile_key} {{
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 4px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.7);
    }}
    
    .hover-meta-{tile_key} {{
        font-size: 0.8rem;
        color: #cccccc;
        margin-bottom: 6px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    }}
    
    .hover-overview-{tile_key} {{
        font-size: 0.75rem;
        line-height: 1.4;
        margin-top: 8px;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    }}
    
    /* Visible Metadata Below - Theme Aware */
    .movie-info-{tile_key} {{
        margin-top: 0.5rem;
        padding: 8px;
        border-radius: 0 0 8px 8px;
        background: rgba(0, 0, 0, 0.6);
        color: #f0f0f0;
    }}
    
    body[data-theme='light'] .movie-info-{tile_key} {{
        background: rgba(255, 255, 255, 0.8);
        color: #111111;
    }}
    
    .movie-title-{tile_key} {{
        font-weight: 600;
        font-size: 0.95rem;
        margin: 0 0 4px 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    .movie-meta-{tile_key} {{
        font-size: 0.75rem;
        margin: 0 0 6px 0;
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
    }}
    
    .movie-genres-{tile_key} {{
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
    }}
    
    .genre-tag-{tile_key} {{
        background: rgba(255,255,255,0.15);
        color: #eeeeee;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 0.65rem;
    }}
    
    /* Scrollbar */
    .hover-panel-{tile_key}::-webkit-scrollbar {{
        width: 4px;
    }}
    
    .hover-panel-{tile_key}::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.3);
        border-radius: 2px;
    }}
    </style>
    
    <div id="tile-{tile_key}" class="movie-tile-{tile_key}" data-theme="{'dark' if is_dark else 'light'}">
        <!-- Poster Image -->
        <img class="movie-poster-{tile_key}" 
             src="{image_url}" 
             alt="{title}"
             loading="{'lazy' if lazy_load else 'eager'}"
             onerror="this.onerror=null;this.src='https://via.placeholder.com/300x450?text=No+Poster'">
        
        <!-- Action Buttons -->
        <div class="action-buttons-{tile_key}">
            <button id="like-{tile_key}" 
                    class="action-button-{tile_key} {'liked' if st.session_state.get(liked_key) else ''}"
                    onclick="handleLike('{tile_key}', '{liked_key}')">
                {'❤️' if st.session_state.get(liked_key) else '♡'}
            </button>
            <button id="watchlist-{tile_key}" 
                    class="action-button-{tile_key} {'added' if st.session_state.get(watchlist_key) else ''}"
                    onclick="handleWatchlist('{tile_key}', '{watchlist_key}')">
                {'✓' if st.session_state.get(watchlist_key) else '+'}
            </button>
        </div>
        
        <!-- Hover Panel -->
        <div class="hover-panel-{tile_key}" onclick="togglePanel('{tile_key}')">
            <div class="hover-title-{tile_key}">{title}</div>
            <div class="hover-meta-{tile_key}">
                <span>🗓 {release_year}</span>
                <span>⭐ {rating_str}</span>
                <span>⏱ {runtime_str}</span>
            </div>
            <div class="hover-overview-{tile_key}">{overview}</div>
        </div>
    </div>
    
    <!-- Visible Metadata -->
    <div class="movie-info-{tile_key}">
        <div class="movie-title-{tile_key}" title="{title}">{title}</div>
        <div class="movie-meta-{tile_key}">
            <span>🗓 {release_year}</span>
            <span>⭐ {rating_str}</span>
            <span>⏱ {runtime_str}</span>
        </div>
        <div class="movie-genres-{tile_key}">
            {"".join(f'<span class="genre-tag-{tile_key}">{g}</span>' for g in genre_tags)}
        </div>
    </div>
    
    <script>
    function togglePanel(tileId) {{
        const tile = document.getElementById(`tile-${{tileId}}`);
        tile.classList.toggle('expanded');
    }}
    
    function handleLike(tileId, likeKey) {{
        event.stopPropagation();
        const btn = document.getElementById(`like-${{tileId}}`);
        const liked = btn.classList.toggle('liked');
        
        btn.innerHTML = liked ? '❤️' : '♡';
        window.parent.postMessage({{
            type: 'movieTileAction',
            action: 'like',
            key: likeKey,
            state: liked,
            title: "{title}"
        }}, '*');
    }}
    
    function handleWatchlist(tileId, watchlistKey) {{
        event.stopPropagation();
        const btn = document.getElementById(`watchlist-${{tileId}}`);
        const added = btn.classList.toggle('added');
        
        btn.innerHTML = added ? '✓' : '+';
        window.parent.postMessage({{
            type: 'movieTileAction',
            action: 'watchlist',
            key: watchlistKey,
            state: added,
            title: "{title}"
        }}, '*');
    }}
    </script>
    """
    
    # Render component
    components.html(html_content, height=580)

# Main app with message handling
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("🎬 MovieTile v9.2 - Complete Fixes")
    
    # Handle messages from components
    components.html(
        """
        <script>
        window.addEventListener("message", (event) => {
            if (event.data.type === "movieTileAction") {
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: JSON.stringify(event.data)
                }, "*");
            }
        });
        </script>
        """,
        height=0
    )
    
    # Check for component messages
    if "_component_value" in st.session_state:
        try:
            action = json.loads(st.session_state["_component_value"])
            st.session_state[action["key"]] = action["state"]
            
            if action["action"] == "like":
                st.toast(f"{'❤️ Liked' if action['state'] else '💔 Unliked'} {action['title']}")
            else:
                st.toast(f"{'➕ Added' if action['state'] else '➖ Removed'} {action['title']} to watchlist")
            
            del st.session_state["_component_value"]
        except Exception as e:
            st.error(f"Error handling action: {str(e)}")
    
    # Theme selector
    theme = st.radio("Theme", ["Light", "Dark"], index=0, horizontal=True)
    st._config.set_option("theme.base", theme.lower())
    
    # Test movies
    test_movies = [
        {
            "title": "The Dark Knight",
            "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
            "overview": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice. With the help of allies Lt. Jim Gordon and DA Harvey Dent, Batman has been able to keep a tight lid on crime in Gotham. But when a vile young criminal calling himself the Joker suddenly throws the town into chaos, the caped Crusader begins to tread a fine line between heroism and vigilantism.",
            "vote_average": 9.0,
            "runtime": 152,
            "release_date": "2008-07-16",
            "genres": [{"name": "Action"}, {"name": "Crime"}, {"name": "Drama"}]
        },
        {
            "title": "Inception",
            "poster_path": "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg",
            "overview": "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: inception, the implantation of another person's idea into a target's subconscious. With a team of specialists, Cobb plans to pull off the reverse heist but their target has defenses that turn the mission into a psychological rollercoaster.",
            "vote_average": 8.4,
            "runtime": 148,
            "release_date": "2010-07-16",
            "genres": [{"name": "Action"}, {"name": "Adventure"}, {"name": "Sci-Fi"}]
        }
    ]
    
    # Display tiles in a grid
    cols = st.columns(2)
    for idx, movie in enumerate(test_movies):
        with cols[idx]:
            MovieTile(movie, testid_suffix=f"movie-{idx}")