import streamlit as st
import streamlit.components.v1 as components
from typing import Union, Optional
import html
import json

def MovieTile(
    movie_data: Union[dict, object],
    testid_suffix: Optional[str] = None,
    lazy_load: bool = True,
    debug: bool = False,
    **kwargs
):
    """
    Movie Tile Component v3.4 - Final Corrected Version
    - Fixed hover behavior exactly as requested
    - Ultra-tight row spacing
    - Correct mobile overview behavior
    - Clean 2D plus icon
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

    # Safely extract and escape data
    def safe_get(key, default=''):
        val = movie_data.get(key)
        if val is None:
            details = movie_data.get('details', {})
            val = details.get(key, default)
        return html.escape(str(val)) if val is not None else default

    title = safe_get('title', 'Untitled')[:50]
    release_date = safe_get('release_date')
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

    overview = safe_get('overview', 'No description available')
    short_overview = (overview[:90] + "...") if len(overview) > 90 else overview
    full_overview = overview if overview != "No description available" else "Description coming soon"

    genres = movie_data.get('genres') or movie_data.get('details', {}).get('genres', [])
    genre_tags = (
        [html.escape(g['name']) for g in genres if isinstance(g, dict) and g.get('name')] or
        [html.escape(g.name) for g in genres if hasattr(g, 'name')] or
        [html.escape(str(g)) for g in genres if g]
    )[:3] or ["No genres"]

    poster_path = safe_get('poster_path')
    if not poster_path:
        image_url = "https://via.placeholder.com/300x450?text=No+Poster"
    elif poster_path.startswith(('http://', 'https://')):
        image_url = poster_path
    else:
        image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"

    # ===== STATE & THEME MANAGEMENT =====
    tile_key = f"mt_{hash(title)}_{testid_suffix or '0'}"
    liked_key = f"{tile_key}_liked"
    watchlist_key = f"{tile_key}_watchlisted"
    
    if liked_key not in st.session_state:
        st.session_state[liked_key] = False
    if watchlist_key not in st.session_state:
        st.session_state[watchlist_key] = False

    # Detect theme
    try:
        theme = st.get_option("theme.base") or "light"
        is_dark = theme == "dark"
        text_color = "#ffffff" if is_dark else "#111111"
        meta_color = "#aaaaaa" if is_dark else "#666666"
        genre_bg = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.05)"
        genre_color = "#cccccc" if is_dark else "#555555"
        genre_border = "#444444" if is_dark else "#eeeeee"
    except:
        is_dark = False
        text_color = "#111111"
        meta_color = "#666666"
        genre_bg = "rgba(0,0,0,0.05)"
        genre_color = "#555555"
        genre_border = "#eeeeee"

    # ===== COMPONENT TEMPLATE =====
    html_content = f"""
    <style>
    /* Container - Ultra-tight spacing */
    .movie-tile-container-{tile_key} {{
        width: 100%;
        margin-bottom: 0.1rem !important;
    }}
    
    .movie-tile-{tile_key} {{
        position: relative;
        width: 100%;
        aspect-ratio: 2/3;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        margin-bottom: 0 !important;
    }}
    
    /* Poster Image */
    .movie-poster-{tile_key} {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    
    /* Action Buttons */
    .action-buttons-{tile_key} {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        gap: 16px;
        z-index: 3;
        opacity: 0;
        transition: opacity 0.2s ease;
        pointer-events: none;
    }}
    
    .action-button-{tile_key} {{
        pointer-events: auto;
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
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }}
    
    .action-button-{tile_key}:hover {{
        transform: scale(1.1);
    }}
    
    .action-button-{tile_key}.liked {{
        color: #ff4d4d !important;
    }}
    
    .action-button-{tile_key}.added {{
        color: #4CAF50 !important;
    }}
    
    /* Plus Icon (2D) */
    .plus-icon {{
        display: inline-block;
        width: 18px;
        height: 18px;
        position: relative;
    }}
    
    .plus-icon::before, .plus-icon::after {{
        content: "";
        position: absolute;
        background: currentColor;
    }}
    
    .plus-icon::before {{
        left: 50%;
        top: 0;
        width: 2px;
        height: 100%;
        margin-left: -1px;
    }}
    
    .plus-icon::after {{
        top: 50%;
        left: 0;
        width: 100%;
        height: 2px;
        margin-top: -1px;
    }}
    
    /* Hover Panel - 1/8 height */
    .hover-panel-{tile_key} {{
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 12.5%;
        background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.7) 70%, transparent 100%);
        color: white;
        padding: 8px 12px;
        transition: all 0.3s ease;
        z-index: 2;
        overflow: hidden;
        backdrop-filter: blur(2px);
        opacity: 0;
        transform: translateY(10px);
    }}
    
    /* Expanded State - Full height */
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
        height: 100%;
        background: rgba(0, 0, 0, 0.88);
        backdrop-filter: blur(4px);
        overflow-y: auto;
        padding: 16px;
        opacity: 1;
        transform: translateY(0);
    }}
    
    /* Hide scrollbar but keep scrollable */
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key}::-webkit-scrollbar {{
        display: none;
    }}
    
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
        -ms-overflow-style: none;
        scrollbar-width: none;
    }}
    
    /* Hover behaviors - EXACTLY AS REQUESTED */
    .movie-tile-{tile_key}:hover .hover-panel-{tile_key}:not(.expanded) {{
        opacity: 1;
        transform: translateY(0);
    }}
    
    /* Hide expanded panel when hover ends */
    .movie-tile-{tile_key}.expanded:not(:hover) .hover-panel-{tile_key} {{
        opacity: 0;
        transform: translateY(10px);
    }}
    
    /* Hide buttons when expanded */
    .movie-tile-{tile_key}.expanded .action-buttons-{tile_key} {{
        display: none;
    }}
    
    /* Show buttons on hover (unless expanded) */
    .movie-tile-{tile_key}:hover .action-buttons-{tile_key}:not(.expanded) {{
        opacity: 1;
    }}
    
    /* Panel Content */
    .hover-title-{tile_key} {{
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 4px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.7);
    }}
    
    .hover-meta-{tile_key} {{
        font-size: 0.85rem;
        color: #dddddd;
        margin-bottom: 4px;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }}
    
    .hover-short-overview-{tile_key} {{
        font-size: 0.8rem;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    .hover-full-overview-{tile_key} {{
        font-size: 0.8rem;
        line-height: 1.4;
        margin-top: 12px;
        display: none;
    }}
    
    .movie-tile-{tile_key}.expanded .hover-short-overview-{tile_key} {{
        display: none;
    }}
    
    .movie-tile-{tile_key}.expanded .hover-full-overview-{tile_key} {{
        display: block;
    }}
    
    /* Visible Metadata Below - Theme Adaptive */
    .movie-info-{tile_key} {{
        margin-top: 0.2rem !important;
        padding: 0 2px;
    }}
    
    .movie-title-{tile_key} {{
        font-weight: 600;
        font-size: 0.95rem;
        margin: 0 0 1px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: {text_color};
    }}
    
    .movie-meta-{tile_key} {{
        font-size: 0.75rem;
        margin: 0 0 2px 0;
        display: flex;
        gap: 8px;
        color: {meta_color};
    }}
    
    .movie-genres-{tile_key} {{
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-bottom: 0 !important;
    }}
    
    .genre-tag-{tile_key} {{
        background: {genre_bg};
        color: {genre_color};
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.65rem;
        border: 1px solid {genre_border};
    }}
    
    /* Mobile optimizations - EXACTLY AS REQUESTED */
    @media (hover: none) {{
        .movie-tile-{tile_key} {{
            -webkit-tap-highlight-color: transparent;
        }}
        
        .hover-panel-{tile_key} {{
            height: 20% !important;
            padding: 10px 12px !important;
            opacity: 1 !important;
            transform: translateY(0) !important;
        }}
        
        .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
            height: 100% !important;
        }}
        
        .action-buttons-{tile_key} {{
            opacity: 1 !important;
        }}
    }}
    </style>
    
    <div class="movie-tile-container-{tile_key}">
        <div id="tile-{tile_key}" class="movie-tile-{tile_key}"
             ontouchstart="this.classList.add('touched')"
             ontouchend="setTimeout(() => this.classList.remove('touched'), 500)"
             onclick="handleTileClick(event, '{tile_key}')">
            
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
                        onclick="handleLike(event, '{tile_key}', '{liked_key}')"
                        aria-label="{'Unlike' if st.session_state.get(liked_key) else 'Like'} this movie">
                    {'❤️' if st.session_state.get(liked_key) else '🤍'}
                </button>
                <button id="watchlist-{tile_key}" 
                        class="action-button-{tile_key} {'added' if st.session_state.get(watchlist_key) else ''}"
                        onclick="handleWatchlist(event, '{tile_key}', '{watchlist_key}')"
                        aria-label="{'Remove from' if st.session_state.get(watchlist_key) else 'Add to'} watchlist">
                    {'✅' if st.session_state.get(watchlist_key) else '<span class="plus-icon"></span>'}
                </button>
            </div>
            
            <!-- Hover Panel -->
            <div class="hover-panel-{tile_key}">
                <div class="hover-title-{tile_key}">{title}</div>
                <div class="hover-meta-{tile_key}">
                    <span>🗓 {release_year}</span>
                    <span>⭐ {rating_str}</span>
                    <span>⏱ {runtime_str}</span>
                </div>
                <div class="hover-short-overview-{tile_key}">{short_overview}</div>
                <div class="hover-full-overview-{tile_key}">{full_overview}</div>
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
    </div>
    
    <script>
    // Handle tile clicks
    function handleTileClick(event, tileId) {{
        const clickedElement = event.target;
        const isActionButton = clickedElement.closest('.action-button-{tile_key}');
        
        if (!isActionButton) {{
            const tile = document.getElementById(`tile-${{tileId}}`);
            
            // If clicking the poster (not the overlay)
            if (clickedElement.classList.contains('movie-poster-{tile_key}')) {{
                // Navigate to details page
                window.parent.postMessage({{
                    type: 'movieNavigation',
                    title: "{title}"
                }}, '*');
                return;
            }}
            
            // If clicking the overlay
            const wasExpanded = tile.classList.contains('expanded');
            tile.classList.toggle('expanded');
            
            if (!wasExpanded) {{
                const panel = tile.querySelector('.hover-panel-{tile_key}');
                panel.scrollTop = 0;
            }}
        }}
    }}
    
    // Like button handler
    function handleLike(event, tileId, likeKey) {{
        event.stopPropagation();
        const btn = document.getElementById(`like-${{tileId}}`);
        const liked = !btn.classList.contains('liked');
        
        btn.classList.toggle('liked');
        btn.innerHTML = liked ? '❤️' : '🤍';
        btn.setAttribute('aria-label', liked ? 'Unlike this movie' : 'Like this movie');
        
        // Bounce animation
        btn.style.transform = 'scale(1.2)';
        setTimeout(() => {{ btn.style.transform = 'scale(1)'; }}, 200);
        
        window.parent.postMessage({{
            type: 'movieTileAction',
            action: 'like',
            key: likeKey,
            state: liked,
            title: "{title}"
        }}, '*');
    }}
    
    // Watchlist button handler
    function handleWatchlist(event, tileId, watchlistKey) {{
        event.stopPropagation();
        const btn = document.getElementById(`watchlist-${{tileId}}`);
        const added = !btn.classList.contains('added');
        
        btn.classList.toggle('added');
        btn.innerHTML = added ? '✅' : '<span class="plus-icon"></span>';
        btn.setAttribute('aria-label', added ? 'Remove from watchlist' : 'Add to watchlist');
        
        // Bounce animation
        btn.style.transform = 'scale(1.2)';
        setTimeout(() => {{ btn.style.transform = 'scale(1)'; }}, 200);
        
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
    
    # Render component with optimized height
    components.html(html_content, height=480)

# Example usage
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("🎬 Ultimate MovieTile Component")
    
    # Message handling
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
            
            if (event.data.type === "movieNavigation") {
                console.log("Navigating to:", event.data.title);
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: JSON.stringify({
                        type: "navigation",
                        title: event.data.title
                    })
                }, "*");
            }
        });
        </script>
        """,
        height=0
    )
    
    # Handle component messages
    if "_component_value" in st.session_state:
        try:
            action = json.loads(st.session_state["_component_value"])
            if action.get("type") == "navigation":
                st.write(f"Navigating to: {action['title']}")
            else:
                st.session_state[action["key"]] = action["state"]
                
                if action["action"] == "like":
                    st.toast(f"{'❤️ Added to Favorites' if action['state'] else '🤍 Removed from Favorites'} - {action['title']}")
                else:
                    st.toast(f"{'✅ Added to Watchlist' if action['state'] else '➕ Removed from Watchlist'} - {action['title']}")
            
            del st.session_state["_component_value"]
        except Exception as e:
            st.error(f"Error handling action: {str(e)}")
    
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
    
    # Display tiles in responsive grid
    cols = st.columns(2)
    for idx, movie in enumerate(test_movies):
        with cols[idx % len(cols)]:
            MovieTile(movie, testid_suffix=f"col{idx}")