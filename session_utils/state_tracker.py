# session_utils/state_tracker.py
import streamlit as st
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from dataclasses import dataclass
from datetime import datetime
from session_utils.date_session_logger import DateSessionLogger

@dataclass
class UserPreferences:
    """Structured user preferences with safe defaults"""
    cinephile_mode: bool = False
    mood_tags: List[str] = None
    critic_persona: str = "balanced"  # [balanced, art_house, mainstream]
    accessibility_mode: bool = False
    dyslexia_font: bool = False

@dataclass
class NavigationState:
    """Track navigation history and context"""
    current_page: str = "home"
    previous_page: Optional[str] = None
    current_movie: Optional[int] = None
    current_actor: Optional[int] = None
    current_director: Optional[int] = None
    search_query: Optional[str] = None

def init_session_state(defaults: Dict[str, Any] = None) -> None:
    """
    Initialize all session state variables with robust defaults
    and load initial CSS assets.
    """
    default_state = {
        "theme": "dark",
        "watchlist": [],
        "search_history": [],
        "navigation": NavigationState(),
        "user_prefs": UserPreferences(),
        "filters": {
            "genres": [],
            "year_range": (2000, 2024),
            "min_rating": 7.0,
            "moods": []
        },
        "last_updated": None,
        "css_initialized": False
    }

    # Set defaults only for missing keys
    for key, value in (defaults or default_state).items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize theme and styles
    sync_theme_to_config()
    if not st.session_state.css_initialized:
        _load_critical_css()
        _load_theme_css()
        st.session_state.css_initialized = True

def _load_critical_css() -> None:
    """Injects minimal CSS to prevent layout shift during load"""
    st.markdown(f"""
    <style>
        :root {{
            --primary: {'#FF4B4B' if get_current_theme() == 'dark' else '#FF2B2B'};
            --bg: {'#0E1117' if get_current_theme() == 'dark' else '#FAFAFA'};
            --text: {'#FAFAFA' if get_current_theme() == 'dark' else '#0E1117'};
            --transition: all 0.3s ease;
        }}
        [data-testid="stAppViewContainer"] {{
            background: var(--bg);
            color: var(--text);
            transition: var(--transition);
        }}
    </style>
    """, unsafe_allow_html=True)

def _load_theme_css() -> None:
    """Loads theme-specific styles from media_assets"""
    theme = get_current_theme()
    css_path = Path("media_assets/styles") / f"{theme}.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", 
                   unsafe_allow_html=True)

def _load_accessibility_css() -> None:
    """Conditionally loads accessibility enhancements"""
    if get_user_prefs().accessibility_mode:
        css_path = Path("media_assets/styles") / "accessibility.css"
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text()}</style>",
                      unsafe_allow_html=True)
    if get_user_prefs().dyslexia_font:
        st.markdown("""
        <style>
            * {
                font-family: 'OpenDyslexic', sans-serif;
            }
        </style>
        """, unsafe_allow_html=True)

def toggle_theme() -> None:
    """Switches theme with visual feedback and CSS reload"""
    new_theme = "light" if get_current_theme() == "dark" else "dark"
    st.session_state.theme = new_theme
    sync_theme_to_config()
    _load_theme_css()
    st.toast(f"Switched to {new_theme} mode", 
             icon="🌙" if new_theme == "dark" else "☀️")

def sync_theme_to_config() -> None:
    """Ensures Streamlit config matches session state"""
    if hasattr(st, '_config') and "theme" in st.session_state:
        st._config.set_option("theme.base", st.session_state.theme)

def get_current_theme() -> str:
    """Safe theme getter with dark mode fallback"""
    return st.session_state.get("theme", "dark")

def reset_user_prefs() -> None:
    """Resets preferences to defaults with visual feedback"""
    st.session_state.user_prefs = UserPreferences()
    _load_accessibility_css()  # Re-load in case accessibility was disabled
    st.toast("Preferences reset to defaults", icon="🔄")

def clear_navigation_states(keep_history: bool = False) -> None:
    """
    Clear temporary navigation-related session states.
    
    Args:
        keep_history: If True, preserves the previous_page value
    """
    if "navigation" not in st.session_state:
        st.session_state.navigation = NavigationState()
        return
    
    # Store previous page if needed
    prev_page = st.session_state.navigation.previous_page if keep_history else None
    
    # Reset navigation state
    st.session_state.navigation = NavigationState(
        previous_page=prev_page,
        current_page=st.session_state.navigation.current_page
    )
    
    # Visual feedback if in an interactive context
    if st.runtime.exists():
        st.toast("Navigation context cleared", icon="🧹")

def navigate_to(page: str) -> None:
    """
    Centralized page navigation with state management
    
    Args:
        page: Target page identifier (e.g., 'home', 'search', 'movie_detail')
    """
    if "navigation" not in st.session_state:
        st.session_state.navigation = NavigationState()
    
    # Update navigation history
    st.session_state.navigation.previous_page = st.session_state.navigation.current_page
    st.session_state.navigation.current_page = page
    
    # Clear transient states when switching major sections
    if page.split('_')[0] != st.session_state.navigation.previous_page.split('_')[0]:
        clear_navigation_states(keep_history=True)

# ---------- Type-safe Getters ----------
def get_watchlist() -> List[Dict]:
    return st.session_state.get("watchlist", [])

def get_active_filters() -> Dict:
    return st.session_state.get("filters", {
        "genres": [],
        "year_range": (2000, 2024),
        "min_rating": 7.0
    })

def get_user_prefs() -> UserPreferences:
    return st.session_state.get("user_prefs", UserPreferences())

def get_navigation_state() -> NavigationState:
    """Get current navigation context with type safety"""
    if "navigation" not in st.session_state:
        st.session_state.navigation = NavigationState()
    return st.session_state.navigation

def update_styles() -> None:
    """Public method to force CSS reload"""
    _load_theme_css()
    _load_accessibility_css()

def update_watchlist(item: Union[int, Dict], remove: bool = False) -> None:
    """
    Add or remove items from watchlist with type safety
    Args:
        item: Either movie ID (int) or full movie dict
        remove: If True, removes the item
    """
    if not hasattr(st.session_state, 'watchlist'):
        st.session_state.watchlist = []
    
    if isinstance(item, int):
        movie_id = item
    elif isinstance(item, dict):
        movie_id = item.get('id')
    else:
        raise TypeError("Item must be int or dict")
    
    if remove:
        st.session_state.watchlist = [
            m for m in st.session_state.watchlist 
            if m.get('id') != movie_id
        ]
    elif not any(m.get('id') == movie_id for m in st.session_state.watchlist):
        if isinstance(item, dict):
            st.session_state.watchlist.append(item)
        else:
            st.session_state.watchlist.append({'id': movie_id})

def get_date_night_status() -> Dict[str, Any]:
    """
    Returns complete date night status including:
    - Active state
    - Blended preferences
    - Original packs
    - Session metadata
    """
    return {
        "is_active": st.session_state.get("date_night_active", False),
        "blended_prefs": st.session_state.get("blended_prefs", {}),
        "original_packs": st.session_state.get("original_packs", {}),
        "session_id": st.session_state.get("date_night_id"),
        "initiated_at": st.session_state.get("date_night_initiated")
    }

def end_date_night() -> None:
    """Cleans up date night mode and returns to normal preferences"""
    if st.session_state.get("date_night_active"):
        # Get session info before clearing
        session_info = get_date_night_status()
        
        # Clear state
        st.session_state.date_night_active = False
        for key in ["blended_prefs", "original_packs", "date_night_id", "date_night_initiated"]:
            st.session_state.pop(key, None)
            
        # UI feedback
        packs = session_info.get("original_packs", {})
        pack_names = [packs.get("pack_a", {}).get("name", "Pack A"), 
                     packs.get("pack_b", {}).get("name", "Pack B")]
        st.toast(f"Date Night ended ({' + '.join(pack_names)})", icon="🎬")

def initiate_date_night(pack_a: Dict[str, Any], pack_b: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize Date Night mode with your movie-based packs"""
    # Validate packs
    REQUIRED_KEYS = {"movies", "moods"}  # Only require what you actually have
    
    for i, pack in enumerate([pack_a, pack_b], 1):
        missing = [k for k in REQUIRED_KEYS if k not in pack]
        if missing:
            raise ValueError(f"Pack {i} missing: {', '.join(missing)}")
        if not isinstance(pack["movies"], list):
            raise ValueError(f"Pack {i} movies must be a list")
        if not isinstance(pack["moods"], dict):
            raise ValueError(f"Pack {i} moods must be a dictionary")

    try:
        from ai_smart_recommender.user_personalization.date_night_blender import (
            blend_packs,
            save_date_session
        )
        
        # Blend using the modified function
        blended_prefs = blend_packs(pack_a, pack_b)
        
        # Save session
        session_id = save_date_session(pack_a, pack_b, blended_prefs)
        
        # Update session state
        st.session_state.update({
            "date_night_active": True,
            "blended_prefs": blended_prefs,
            "original_packs": {
                "pack_a": pack_a,
                "pack_b": pack_b
            },
            "date_night_id": session_id,
            "date_night_initiated": datetime.now().isoformat()
        })
        
        st.toast(f"Date Night started with {pack_a.get('name', 'Pack A')} + {pack_b.get('name', 'Pack B')}", icon="❤️")
        return blended_prefs
        
    except Exception as e:
        st.error(f"Failed to activate Date Night: {str(e)}")
        raise
    
def is_date_night_active() -> bool:
    """Check if date night mode is currently active"""
    return st.session_state.get("date_night_active", False)

def get_blended_prefs() -> Dict[str, Any]:
    """Returns the current blended preferences if Date Night is active"""
    if st.session_state.get("date_night_active", False):
        return st.session_state.get("blended_prefs", {})
    return {}
def get_current_director() -> Optional[Dict]:
    """Get current director from navigation state with type safety"""
    if "navigation" not in st.session_state:
        return None
    director_id = st.session_state.navigation.current_director
    if not director_id:
        return None
    
    # Return minimal director info if no full object is stored
    return {
        "id": director_id,
        "name": st.session_state.get("current_director_name", "Unknown Director"),
        "profile_path": st.session_state.get("current_director_profile_path")
    }

def set_current_director(director_id: int, name: str = None, profile_path: str = None) -> None:
    """Set current director in navigation state"""
    if "navigation" not in st.session_state:
        st.session_state.navigation = NavigationState()
    
    st.session_state.navigation.current_director = director_id
    if name:
        st.session_state["current_director_name"] = name
    if profile_path:
        st.session_state["current_director_profile_path"] = profile_path


def get_mood_for_date(date_str: str) -> Optional[str]:
    """
    Get the selected mood for a given date (ISO string).
    Returns None if no mood is set.
    """
    selected_moods = st.session_state.get("selected_moods", {})
    return selected_moods.get(date_str)

def set_mood_for_date(date_str: str, mood: str):
    """
    Set a mood for a specific date in session state.
    """
    if "selected_moods" not in st.session_state:
        st.session_state.selected_moods = {}
    st.session_state.selected_moods[date_str] = mood