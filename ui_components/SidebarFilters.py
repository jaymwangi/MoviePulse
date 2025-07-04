# ui_components/SidebarFilters.py
import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from urllib.parse import parse_qs
from session_utils.state_tracker import get_current_theme
from session_utils.session_helpers import load_genres, load_moods

# Constants
DEFAULT_YEAR_RANGE = (2000, datetime.now().year)
DEFAULT_RATING_RANGE = (7.0, 10.0)
DEFAULT_POPULARITY_RANGE = (0, 100)
GENRES_FILE = "static_data/genres.json"
DEBOUNCE_TIME = 0.5  # Seconds to wait before applying filter changes

def _init_session_state():
    """Initialize session state with URL params or defaults"""
    if "filter_init_complete" not in st.session_state:
        url_params = st.query_params.to_dict()
        
        def safe_parse(value, type_func, default=None):
            try:
                return type_func(value) if value else default
            except (ValueError, TypeError):
                return default
        
        # Initialize with defaults or URL values
        st.session_state.update({
            "selected_genres": url_params.get("genres", "").split(",") if url_params.get("genres") else [],
            "selected_moods": [int(m) for m in url_params.get("moods", "").split(",") if m.isdigit()] if url_params.get("moods") else [],
            "year_range": (
                safe_parse(url_params.get("year_min"), int, DEFAULT_YEAR_RANGE[0]),
                safe_parse(url_params.get("year_max"), int, DEFAULT_YEAR_RANGE[1])
            ),
            "exact_year": safe_parse(url_params.get("exact_year"), int),
            "rating_range": (
                safe_parse(url_params.get("rating_min"), float, DEFAULT_RATING_RANGE[0]),
                safe_parse(url_params.get("rating_max"), float, DEFAULT_RATING_RANGE[1])
            ),
            "exact_rating": safe_parse(url_params.get("exact_rating"), float),
            "popularity_range": (
                safe_parse(url_params.get("popularity_min"), int, DEFAULT_POPULARITY_RANGE[0]),
                safe_parse(url_params.get("popularity_max"), int, DEFAULT_POPULARITY_RANGE[1])
            ),
            "exact_popularity": safe_parse(url_params.get("exact_popularity"), int),
            "last_filter_change": 0,
            "filter_init_complete": True,
            "year_filter_mode": "range" if not url_params.get("exact_year") else "exact",
            "rating_filter_mode": "range" if not url_params.get("exact_rating") else "exact",
            "popularity_filter_mode": "range" if not url_params.get("exact_popularity") else "exact"
        })

def _validate_current_state():
    """Ensure session state values are valid"""
    # Validate genres
    valid_genres = [g["name"] for g in load_genres()]
    st.session_state.selected_genres = [
        g for g in st.session_state.selected_genres 
        if g in valid_genres
    ]
    
    # Validate moods
    valid_mood_ids = [mood["id"] for mood in load_moods()]
    st.session_state.selected_moods = [
        m for m in st.session_state.selected_moods
        if m in valid_mood_ids
    ]
    
    
    # Validate year values
    if st.session_state.year_filter_mode == "exact" and st.session_state.exact_year:
        st.session_state.exact_year = max(1950, min(int(st.session_state.exact_year), datetime.now().year))
    else:
        min_year, max_year = st.session_state.year_range
        st.session_state.year_range = (
            max(1950, min(min_year, datetime.now().year)),
            min(datetime.now().year, max(max_year, 1950))
        )
    
    # Validate rating values
    if st.session_state.rating_filter_mode == "exact" and st.session_state.exact_rating:
        st.session_state.exact_rating = max(0.0, min(float(st.session_state.exact_rating), 10.0))
    else:
        min_rating, max_rating = st.session_state.rating_range
        st.session_state.rating_range = (
            max(0.0, min(min_rating, 10.0)),
            min(10.0, max(max_rating, 0.0))
        )
    
    # Validate popularity values
    if st.session_state.popularity_filter_mode == "exact" and st.session_state.exact_popularity:
        st.session_state.exact_popularity = max(0, min(int(st.session_state.exact_popularity), 100))
    else:
        min_pop, max_pop = st.session_state.popularity_range
        st.session_state.popularity_range = (
            max(0, min(min_pop, 100)),
            min(100, max(max_pop, 0))
        )

def _sync_state_to_url():
    """Update URL parameters to reflect current filters"""
    params = {
        "genres": ",".join(st.session_state.selected_genres),
        "moods": ",".join(map(str, st.session_state.selected_moods)),
        "year_min": str(st.session_state.year_range[0]),
        "year_max": str(st.session_state.year_range[1]),
        "rating_min": str(st.session_state.rating_range[0]),
        "rating_max": str(st.session_state.rating_range[1]),
        "popularity_min": str(st.session_state.popularity_range[0]),
        "popularity_max": str(st.session_state.popularity_range[1])
    }
    
    if st.session_state.year_filter_mode == "exact" and st.session_state.exact_year:
        params["exact_year"] = str(st.session_state.exact_year)
    if st.session_state.rating_filter_mode == "exact" and st.session_state.exact_rating:
        params["exact_rating"] = str(st.session_state.exact_rating)
    if st.session_state.popularity_filter_mode == "exact" and st.session_state.exact_popularity:
        params["exact_popularity"] = str(st.session_state.exact_popularity)
    
    st.query_params.update(**params)

def reset_filters():
    """Reset all filters to defaults"""
    st.session_state.update({
        "selected_genres": [],
        "selected_moods": [],
        "year_range": DEFAULT_YEAR_RANGE,
        "exact_year": None,
        "rating_range": DEFAULT_RATING_RANGE,
        "exact_rating": None,
        "popularity_range": DEFAULT_POPULARITY_RANGE,
        "exact_popularity": None,
        "year_filter_mode": "range",
        "rating_filter_mode": "range",
        "popularity_filter_mode": "range",
        "last_filter_change": datetime.now().timestamp()
    })
    _sync_state_to_url()
    st.toast("Filters reset to defaults", icon="♻️")

def get_active_filters() -> Dict:
    """Returns current filters in API-ready format"""
    filters = {
        "genres": st.session_state.selected_genres,
        "moods": st.session_state.selected_moods,
        "ready": _should_trigger_search()
    }
    
    if st.session_state.year_filter_mode == "exact" and st.session_state.exact_year:
        filters["year"] = int(st.session_state.exact_year)
    else:
        filters["year_range"] = st.session_state.year_range
    
    if st.session_state.rating_filter_mode == "exact" and st.session_state.exact_rating:
        filters["rating"] = float(st.session_state.exact_rating)
    else:
        filters["rating_range"] = st.session_state.rating_range
    
    if st.session_state.popularity_filter_mode == "exact" and st.session_state.exact_popularity:
        filters["popularity"] = int(st.session_state.exact_popularity)
    else:
        filters["popularity_range"] = st.session_state.popularity_range
    
    return filters

def _should_trigger_search() -> bool:
    """Determine if we should trigger a new search"""
    if "last_filter_change" not in st.session_state:
        return False
    time_since_change = datetime.now().timestamp() - st.session_state.last_filter_change
    return time_since_change >= DEBOUNCE_TIME

def render_sidebar_filters():
    """Main sidebar rendering function"""
    _init_session_state()
    _validate_current_state()
    
    with st.sidebar:
        st.markdown(f"""
        <style>
            .sidebar-header {{
                color: {'#FAFAFA' if get_current_theme() == 'dark' else '#0E1117'};
                font-size: 1.3rem;
                margin-bottom: 1rem;
            }}
            .filter-expander {{
                margin-bottom: 1.5rem;
            }}
            .range-display {{
                background: {'#2e2e2e' if get_current_theme() == 'dark' else '#f0f2f6'};
                padding: 8px;
                border-radius: 8px;
                text-align: center;
                margin-top: -10px;
                margin-bottom: 10px;
            }}
            .filter-toggle {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.5rem;
            }}
            .mood-option {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
        </style>
        <div class="sidebar-header">🎬 Filter Movies</div>
        """, unsafe_allow_html=True)
        
        filter_changed = False
        
        # ---- GENRE SELECTOR ----
        with st.expander("**🎭 Genres**", expanded=True):
            all_genres = load_genres()
            selected = st.multiselect(
                "Select genres",
                options=[g["name"] for g in all_genres],
                default=st.session_state.selected_genres,
                key="genre_selector",
                label_visibility="collapsed",
                on_change=lambda: st.session_state.update({
                    "last_filter_change": datetime.now().timestamp()
                })
            )
            
            if selected != st.session_state.selected_genres:
                filter_changed = True
                st.session_state.selected_genres = selected
            
            if selected:
                st.caption(f"📌 {len(selected)} selected")


        # ---- MOOD SELECTOR ----
        with st.expander("**😊 Moods**", expanded=True):
            all_moods = load_moods()  # This returns a list of mood dictionaries
            
            # Create display options with (id, display_text)
            mood_options = [
                (mood["id"], f"{mood.get('icon', '🎬')} {mood['name']}") 
                for mood in all_moods
            ]
            
            # Get currently selected mood labels
            selected_ids = st.session_state.selected_moods
            selected_labels = [
                label for (id, label) in mood_options 
                if id in selected_ids
            ]
            
            # Render the multiselect with descriptions as tooltips
            selected_labels = st.multiselect(
                "Select moods",
                options=[label for (id, label) in mood_options],
                default=selected_labels,
                key="mood_selector",
                label_visibility="collapsed",
                help="Select one or more moods to filter by",
                on_change=lambda: st.session_state.update({
                    "last_filter_change": datetime.now().timestamp()
                })
            )
            
            # Show descriptions for selected moods
            if selected_labels:
                st.caption("Selected moods:")
                for mood in all_moods:
                    if f"{mood.get('icon', '🎬')} {mood['name']}" in selected_labels:
                        st.caption(f"• {mood['description']}")
            
            # Map selected labels back to mood IDs
            new_selected_ids = [
                id for (id, label) in mood_options 
                if label in selected_labels
            ]
            
            if new_selected_ids != st.session_state.selected_moods:
                st.session_state.selected_moods = new_selected_ids
                st.session_state.last_filter_change = datetime.now().timestamp()

        # ---- YEAR FILTER ----
        with st.expander("**📅 Release Year**", expanded=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Range", 
                           key="year_range_btn", 
                           disabled=st.session_state.year_filter_mode == "range"):
                    st.session_state.year_filter_mode = "range"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            with col2:
                if st.button("Exact Year",
                           key="year_exact_btn",
                           disabled=st.session_state.year_filter_mode == "exact"):
                    st.session_state.year_filter_mode = "exact"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            
            if st.session_state.year_filter_mode == "exact":
                exact_year = st.number_input(
                    "Select exact year",
                    min_value=1950,
                    max_value=datetime.now().year,
                    value=int(st.session_state.exact_year) if st.session_state.exact_year else datetime.now().year,
                    step=1,
                    key="exact_year_input",
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if exact_year != st.session_state.exact_year:
                    filter_changed = True
                    st.session_state.exact_year = exact_year
                
                st.markdown(
                    f"<div class='range-display'><b>📅 {exact_year}</b></div>",
                    unsafe_allow_html=True
                )
            else:
                year_range = st.slider(
                    "Select year range",
                    min_value=1950,
                    max_value=datetime.now().year,
                    value=st.session_state.year_range,
                    key="year_slider",
                    step=1,
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if year_range != st.session_state.year_range:
                    filter_changed = True
                    st.session_state.year_range = year_range
                
                if year_range[0] == year_range[1]:
                    st.markdown(
                        f"<div class='range-display'><b>📅 {year_range[0]}</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='range-display'><b>📅 {year_range[0]} - {year_range[1]}</b></div>",
                        unsafe_allow_html=True
                    )

        # ---- RATING FILTER ----
        with st.expander("**⭐ Rating**", expanded=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Range", 
                           key="rating_range_btn", 
                           disabled=st.session_state.rating_filter_mode == "range"):
                    st.session_state.rating_filter_mode = "range"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            with col2:
                if st.button("Exact Rating",
                           key="rating_exact_btn",
                           disabled=st.session_state.rating_filter_mode == "exact"):
                    st.session_state.rating_filter_mode = "exact"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            
            if st.session_state.rating_filter_mode == "exact":
                exact_rating = st.number_input(
                    "Select exact rating",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(st.session_state.exact_rating) if st.session_state.exact_rating else 7.0,
                    step=0.1,
                    format="%.1f",
                    key="exact_rating_input",
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if exact_rating != st.session_state.exact_rating:
                    filter_changed = True
                    st.session_state.exact_rating = exact_rating
                
                st.markdown(
                    f"<div class='range-display'><b>🌟 {exact_rating:.1f}</b></div>",
                    unsafe_allow_html=True
                )
            else:
                rating_range = st.slider(
                    "Select rating range",
                    min_value=0.0,
                    max_value=10.0,
                    value=st.session_state.rating_range,
                    step=0.1,
                    format="%.1f",
                    key="rating_slider",
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if rating_range != st.session_state.rating_range:
                    filter_changed = True
                    st.session_state.rating_range = rating_range
                
                if rating_range[0] == rating_range[1]:
                    st.markdown(
                        f"<div class='range-display'><b>🌟 Exactly {rating_range[0]:.1f}</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='range-display'><b>🌟 {rating_range[0]:.1f} - {rating_range[1]:.1f}</b></div>",
                        unsafe_allow_html=True
                    )

        # ---- POPULARITY FILTER ----
        with st.expander("**📈 Popularity**", expanded=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Range", 
                           key="popularity_range_btn", 
                           disabled=st.session_state.popularity_filter_mode == "range"):
                    st.session_state.popularity_filter_mode = "range"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            with col2:
                if st.button("Exact Value",
                           key="popularity_exact_btn",
                           disabled=st.session_state.popularity_filter_mode == "exact"):
                    st.session_state.popularity_filter_mode = "exact"
                    filter_changed = True
                    st.session_state.last_filter_change = datetime.now().timestamp()
            
            if st.session_state.popularity_filter_mode == "exact":
                exact_popularity = st.number_input(
                    "Select exact popularity",
                    min_value=0,
                    max_value=100,
                    value=int(st.session_state.exact_popularity) if st.session_state.exact_popularity else 50,
                    step=1,
                    key="exact_popularity_input",
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if exact_popularity != st.session_state.exact_popularity:
                    filter_changed = True
                    st.session_state.exact_popularity = exact_popularity
                
                st.markdown(
                    f"<div class='range-display'><b>📊 {exact_popularity}</b></div>",
                    unsafe_allow_html=True
                )
            else:
                popularity_range = st.slider(
                    "Select popularity range",
                    min_value=0,
                    max_value=100,
                    value=st.session_state.popularity_range,
                    key="popularity_slider",
                    on_change=lambda: st.session_state.update({
                        "last_filter_change": datetime.now().timestamp()
                    })
                )
                
                if popularity_range != st.session_state.popularity_range:
                    filter_changed = True
                    st.session_state.popularity_range = popularity_range
                
                if popularity_range[0] == popularity_range[1]:
                    st.markdown(
                        f"<div class='range-display'><b>📊 Exactly {popularity_range[0]}</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='range-display'><b>📊 {popularity_range[0]} - {popularity_range[1]}</b></div>",
                        unsafe_allow_html=True
                    )

        # ---- FEEDBACK & CONTROLS ----
        st.divider()
        
        if filter_changed and not _should_trigger_search():
            with st.spinner("Applying filters..."):
                st.write("")
            _sync_state_to_url()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(
                "♻️ Reset All Filters",
                use_container_width=True,
                help="Clear all current filters"
            ):
                reset_filters()
        
        with col2:
            active_filters = sum([
                len(st.session_state.selected_genres) > 0,
                len(st.session_state.selected_moods) > 0,
                st.session_state.year_filter_mode == "exact" or st.session_state.year_range != DEFAULT_YEAR_RANGE,
                st.session_state.rating_filter_mode == "exact" or st.session_state.rating_range != DEFAULT_RATING_RANGE,
                st.session_state.popularity_filter_mode == "exact" or st.session_state.popularity_range != DEFAULT_POPULARITY_RANGE
            ])
            st.markdown(f"""
            <div style="
                background: {'#555' if get_current_theme() == 'dark' else '#eee'};
                color: {'white' if get_current_theme() == 'dark' else 'black'};
                border-radius: 1rem;
                padding: 0.25rem 0.5rem;
                text-align: center;
                font-size: 0.8rem;
            ">
                {active_filters} active
            </div>
            """, unsafe_allow_html=True)