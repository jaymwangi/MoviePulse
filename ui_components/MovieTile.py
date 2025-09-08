import streamlit as st
import streamlit.components.v1 as components
from typing import Union, Optional, Literal
import html
import json
from datetime import datetime

def show_movie_toast(
    action_type: Literal["like", "unlike", "watchlist_add", "watchlist_remove"],
    movie_title: str,
    icon: str = "🎬",
    duration: int = 3000
):
    """Enhanced toast notification system for movie actions"""
    messages = {
        "like": f"{icon} Added to Favorites",
        "unlike": f"{icon} Removed from Favorites",
        "watchlist_add": f"{icon} Added to Watchlist",
        "watchlist_remove": f"{icon} Removed from Watchlist"
    }
    
    # Get the appropriate message
    message = messages.get(action_type, f"{icon} Movie action completed")
    
    # Create a more detailed toast
    toast_html = f"""
    <style>
    .movie-toast {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: rgba(32, 33, 36, 0.9);
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-left: 4px solid;
        animation: fadeIn 0.3s ease-out;
    }}
    
    .movie-toast.like {{
        border-color: #ff4d4d;
    }}
    
    .movie-toast.unlike {{
        border-color: #ff9999;
    }}
    
    .movie-toast.watchlist_add {{
        border-color: #4CAF50;
    }}
    
    .movie-toast.watchlist_remove {{
        border-color: #81C784;
    }}
    
    .movie-toast-icon {{
        font-size: 1.5rem;
    }}
    
    .movie-toast-content {{
        display: flex;
        flex-direction: column;
    }}
    
    .movie-toast-title {{
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 2px;
    }}
    
    .movie-toast-message {{
        font-size: 0.85rem;
        opacity: 0.9;
    }}
    
    .movie-toast-time {{
        font-size: 0.75rem;
        opacity: 0.7;
        margin-top: 4px;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    
    <div class="movie-toast {action_type}">
        <div class="movie-toast-icon">{icon}</div>
        <div class="movie-toast-content">
            <div class="movie-toast-title">{movie_title}</div>
            <div class="movie-toast-message">{message}</div>
            <div class="movie-toast-time">{datetime.now().strftime("%H:%M")}</div>
        </div>
    </div>
    """
    
    # Show the toast
    components.html(toast_html, height=80)

def MovieTile(
    movie_data: Union[dict, object],
    testid_suffix: Optional[str] = None,
    lazy_load: bool = True,
    debug: bool = False,
    tldr_data: Optional[dict] = None,
    **kwargs
):
    """
    Movie Tile Component v4.1 - Enhanced with TL;DR preview in hover panel
    - Zoom effect on hover
    - TL;DR preview display in hover panel instead of TMDB overview
    - Optimized for large grids
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

    # Process TL;DR data - check if tldr_data is provided or if it's in movie_data
    tldr_summary = ""
    tldr_themes = []
    tldr_flags = []
    
    # First check if tldr_data parameter is provided
    if tldr_data:
        tldr_summary = html.escape(tldr_data.get('summary', ''))
        tldr_themes = [html.escape(theme) for theme in tldr_data.get('themes', [])[:3]]
        tldr_flags = [html.escape(flag) for flag in tldr_data.get('flags', [])[:2]]
    # If not, check if there's tldr data in the movie_data itself
    elif 'tldr' in movie_data and movie_data['tldr']:
        tldr_data = movie_data['tldr']
        tldr_summary = html.escape(tldr_data.get('summary', ''))
        tldr_themes = [html.escape(theme) for theme in tldr_data.get('themes', [])[:3]]
        tldr_flags = [html.escape(flag) for flag in tldr_data.get('flags', [])[:2]]

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
    /* Container - Perfect spacing */
    .movie-tile-container-{tile_key} {{
        width: 100%;
        margin-bottom: 0.5rem !important;
        position: relative;
    }}
    
    /* Poster container with enhanced hover effects */
    .movie-tile-{tile_key} {{
        position: relative;
        width: 100%;
        aspect-ratio: 2/3;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        margin-bottom: 0 !important;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transform-origin: center;
    }}
    
    /* Enhanced hover effects */
    .movie-tile-{tile_key}:hover {{
        transform: scale(1.05);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        z-index: 10;
    }}
    
    /* Poster image with subtle hover effect */
    .movie-poster-{tile_key} {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        transition: all 0.3s ease;
    }}
    
    .movie-tile-{tile_key}:hover .movie-poster-{tile_key} {{
        transform: scale(1.08);
        filter: brightness(1.05);
    }}
    
    /* Action buttons */
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
    
    /* Plus icon styling */
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
    
    /* Hover panel styling - UPDATED FOR TL;DR */
    .hover-panel-{tile_key} {{
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 12.5%;
        background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.8) 70%, transparent 100%);
        color: white;
        padding: 8px 12px;
        transition: all 0.3s ease;
        z-index: 2;
        overflow: hidden;
        backdrop-filter: blur(2px);
        opacity: 0;
        transform: translateY(10px);
    }}
    
    /* Expanded state */
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        backdrop-filter: blur(4px);
        overflow-y: auto;
        padding: 16px;
        opacity: 1;
        transform: translateY(0);
    }}
    
    /* Hide scrollbar */
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key}::-webkit-scrollbar {{
        display: none;
    }}
    
    .movie-tile-{tile_key}.expanded .hover-panel-{tile_key} {{
        -ms-overflow-style: none;
        scrollbar-width: none;
    }}
    
    /* Hover behaviors */
    .movie-tile-{tile_key}:hover .hover-panel-{tile_key}:not(.expanded) {{
        opacity: 1;
        transform: translateY(0);
    }}
    
    .movie-tile-{tile_key}.expanded:not(:hover) .hover-panel-{tile_key} {{
        opacity: 0;
        transform: translateY(10px);
    }}
    
    /* Hide buttons when expanded */
    .movie-tile-{tile_key}.expanded .action-buttons-{tile_key} {{
        display: none;
    }}
    
    /* Show buttons on hover */
    .movie-tile-{tile_key}:hover .action-buttons-{tile_key}:not(.expanded) {{
        opacity: 1;
    }}
    
    /* Panel content - UPDATED FOR TL;DR */
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
    
    /* TL;DR Section in Hover Panel */
    .tldr-section-{tile_key} {{
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.2);
    }}
    
    .tldr-label-{tile_key} {{
        font-weight: 600;
        font-size: 0.8rem;
        color: #FFD700;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 4px;
    }}
    
    .tldr-summary-{tile_key} {{
        font-size: 0.8rem;
        line-height: 1.3;
        margin-bottom: 6px;
        color: #ffffff;
    }}
    
    .tldr-themes-{tile_key} {{
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 6px;
    }}
    
    .tldr-theme-tag-{tile_key} {{
        background: rgba(255, 215, 0, 0.2);
        color: #FFD700;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 0.7rem;
        border: 1px solid rgba(255, 215, 0, 0.3);
    }}
    
    .tldr-flags-{tile_key} {{
        display: flex;
        gap: 6px;
        font-size: 0.75rem;
        opacity: 0.8;
    }}
    
    /* Full overview section (shown only when expanded) */
    .full-overview-section-{tile_key} {{
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.2);
        display: none;
    }}
    
    .full-overview-label-{tile_key} {{
        font-weight: 600;
        font-size: 0.8rem;
        color: #4FC3F7;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 4px;
    }}
    
    .hover-full-overview-{tile_key} {{
        font-size: 0.8rem;
        line-height: 1.4;
        color: #dddddd;
    }}
    
    .movie-tile-{tile_key}.expanded .full-overview-section-{tile_key} {{
        display: block;
    }}
    
    /* ===== PERFECT METADATA LAYOUT ===== */
    .movie-info-{tile_key} {{
        margin-top: 0.8rem;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        width: 100%;
        position: relative;
    }}
    
    .movie-title-{tile_key} {{
        font-weight: 600;
        font-size: clamp(0.95rem, 1.6vw, 1.05rem);
        margin: 0;
        padding: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: {text_color};
        line-height: 1.3;
        transition: all 0.2s ease;
    }}
    
    .movie-meta-{tile_key} {{
        font-size: clamp(0.78rem, 1.4vw, 0.88rem);
        margin: 0;
        padding: 0;
        display: flex;
        gap: 1.1rem;
        color: {meta_color};
        line-height: 1.3;
        flex-wrap: nowrap;
        overflow: hidden;
        justify-content: center;
    }}
    
    .movie-meta-{tile_key} span {{
        white-space: nowrap;
        flex-shrink: 0;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }}
    
    .movie-genres-{tile_key} {{
        display: flex;
        gap: 0.7rem;
        flex-wrap: wrap;
        margin: 0;
        padding: 0;
        justify-content: flex-start;
    }}
    
    .genre-tag-{tile_key} {{
        background: {genre_bg};
        color: {genre_color};
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: clamp(0.68rem, 1.2vw, 0.78rem);
        border: 1px solid {genre_border};
        line-height: 1.3;
        flex-shrink: 0;
    }}

    /* Mobile optimizations */
    @media (max-width: 480px) {{
        .movie-meta-{tile_key} {{
            gap: 0.8rem;
            font-size: 0.75rem;
            justify-content: flex-start;
        }}
        
        .movie-title-{tile_key} {{
            font-size: 0.9rem;
        }}
        
        .genre-tag-{tile_key} {{
            font-size: 0.65rem;
            padding: 0.25rem 0.7rem;
        }}
        
        .movie-info-{tile_key} {{
            margin-top: 0.7rem;
            gap: 0.5rem;
        }}
        
        .action-button-{tile_key} {{
            width: 38px;
            height: 38px;
            font-size: 1rem;
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
            
            <!-- Hover Panel - UPDATED TO SHOW TL;DR -->
            <div class="hover-panel-{tile_key}">
                <div class="hover-title-{tile_key}">{title}</div>
                <div class="hover-meta-{tile_key}">
                    <span>🗓 {release_year}</span>
                    <span>⭐ {rating_str}</span>
                    <span>⏱ {runtime_str}</span>
                </div>
                
                <!-- TL;DR Section -->
                <div class="tldr-section-{tile_key}">
                    <div class="tldr-label-{tile_key}">📝 TL;DR Preview:</div>
                    {f'<div class="tldr-summary-{tile_key}">"{tldr_summary}"</div>' if tldr_summary else f'<div class="tldr-summary-{tile_key}">No TL;DR available yet</div>'}
                    
                    {f'<div class="tldr-themes-{tile_key}">{"".join(f"<span class=\"tldr-theme-tag-{tile_key}\">{theme}</span>" for theme in tldr_themes)}</div>' if tldr_themes else ''}
                    
                    {f'<div class="tldr-flags-{tile_key}">{" ".join(tldr_flags)}</div>' if tldr_flags else ''}
                </div>
                
                <!-- Full Overview Section (shown only when expanded) -->
                <div class="full-overview-section-{tile_key}">
                    <div class="full-overview-label-{tile_key}">🌐 Full Overview:</div>
                    <div class="hover-full-overview-{tile_key}">{full_overview}</div>
                </div>
            </div>
        </div>
        
        <!-- Visible Metadata - PERFECT SPACING -->
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
    components.html(html_content, height=500)

# Example usage
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("🎬 Enhanced MovieTile Component with TL;DR Preview")
    
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
                prev_state = st.session_state.get(action["key"], False)
                st.session_state[action["key"]] = action["state"]
                
                # Determine the action type for toast
                if action["action"] == "like":
                    action_type = "like" if action["state"] else "unlike"
                    icon = "❤️" if action["state"] else "💔"
                else:
                    action_type = "watchlist_add" if action["state"] else "watchlist_remove"
                    icon = "✅" if action["state"] else "❌"
                
                # Show the enhanced toast
                show_movie_toast(
                    action_type=action_type,
                    movie_title=action["title"],
                    icon=icon,
                    duration=3000
                )
            
            del st.session_state["_component_value"]
        except Exception as e:
            st.error(f"Error handling action: {str(e)}")
    
    # Test movies with TL;DR data
    test_movies = [
        {
            "title": "The Dark Knight",
            "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
            "overview": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice. With the help of allies Lt. Jim Gordon and DA Harvey Dent, Batman has been able to keep a tight lid on crime in Gotham. But when a vile young criminal calling himself the Joker suddenly throws the town into chaos, the caped Crusader begins to tread a fine line between heroism and vigilantism.",
            "vote_average": 9.0,
            "runtime": 152,
            "release_date": "2008-07-16",
            "genres": [{"name": "Action"}, {"name": "Crime"}, {"name": "Drama"}],
            "tldr": {
                "summary": "Batman battles the chaotic Joker in a psychological war for Gotham's soul.",
                "themes": ["Chaos vs Order", "Dual Identity", "Moral Limits"],
                "flags": ["⚠️ Intense Violence", "🧠 Psychological Themes"]
            }
        },
        {
            "title": "Inception",
            "poster_path": "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg",
            "overview": "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: inception, the implantation of another person's idea into a target's subconscious. With a team of specialists, Cobb plans to pull off the reverse heist but their target has defenses that turn the mission into a psychological rollercoaster.",
            "vote_average": 8.4,
            "runtime": 148,
            "release_date": "2010-07-16",
            "genres": [{"name": "Action"}, {"name": "Adventure"}, {"name": "Sci-Fi"}],
            "tldr": {
                "summary": "Dream thieves attempt to plant an idea in a target's subconscious.",
                "themes": ["Reality vs Dreams", "Guilt & Redemption", "Architecture of Mind"],
                "flags": ["🌀 Complex Plot", "🧠 Mind-bending"]
            }
        },
        {
            "title": "The Shawshank Redemption",
            "poster_path": "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
            "overview": "Framed in the 1940s for the double murder of his wife and her lover, upstanding banker Andy Dufresne begins a new life at the Shawshank prison, where he puts his accounting skills to work for an amoral warden. During his long stretch in prison, Dufresne comes to be admired by the other inmates -- including an older prisoner named Red -- for his integrity and unquenchable sense of hope.",
            "vote_average": 9.3,
            "runtime": 142,
            "release_date": "1994-09-23",
            "genres": [{"name": "Drama"}, {"name": "Crime"}],
            "tldr": {
                "summary": "A banker maintains hope and dignity while serving a life sentence.",
                "themes": ["Hope & Perseverance", "Friendship", "Institutionalization"],
                "flags": ["🔞 Prison Violence", "💔 Emotional Themes"]
            }
        }
    ]
    
    # Display tiles in responsive grid - FIXED: Don't pop the tldr data
    cols = st.columns(3)
    for idx, movie in enumerate(test_movies):
        with cols[idx % len(cols)]:
            # Pass the tldr data directly from the movie dictionary
            MovieTile(movie, testid_suffix=f"col{idx}", tldr_data=movie.get("tldr"))