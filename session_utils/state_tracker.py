# session_utils/state_tracker.py
import streamlit as st
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class UserPreferences:
    """Structured user preferences with safe defaults"""
    cinephile_mode: bool = False
    mood_tags: List[str] = None
    critic_persona: str = "balanced"  # [balanced, art_house, mainstream]
    accessibility_mode: bool = False
    dyslexia_font: bool = False

def init_session_state(defaults: Dict[str, Any] = None) -> None:
    """
    Initialize all session state variables with robust defaults
    and load initial CSS assets.
    """
    default_state = {
        "theme": "dark",
        "watchlist": [],
        "search_history": [],
        "current_page": "home",
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

def update_styles() -> None:
    """Public method to force CSS reload"""
    _load_theme_css()
    _load_accessibility_css()