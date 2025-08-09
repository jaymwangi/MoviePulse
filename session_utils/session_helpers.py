"""
session_helpers.py - Core session state and data management for MoviePulse

Handles:
- Session initialization
- State persistence
- Data loading (genres, moods, etc.)
- User profile management
"""

import json
import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Constants
SESSION_DIR = Path("session_data")
USER_PROFILES_PATH = Path("static_data/user_profiles.json")
STARTER_PACKS_PATH = Path("static_data/starter_packs.json")
GENRES_PATH = Path("static_data/genres.json")
MOODS_PATH = Path("static_data/moods.json")

class SessionHelper:
    def __init__(self):
        self._ensure_session_dir()
        self._initialize_core_state()
        
    def _ensure_session_dir(self) -> None:
        """Create session directory if it doesn't exist"""
        SESSION_DIR.mkdir(exist_ok=True)
        
    def _initialize_core_state(self) -> None:
        """Initialize essential session state variables"""
        if "app_initialized" not in st.session_state:
            st.session_state.update({
                "app_initialized": True,
                "current_page": "Home",
                "last_activity": datetime.now().isoformat(),
                "user_profile": self._load_user_profile(),
                "watchlist": self._load_watchlist(),
                "starter_pack": None,
                "active_filters": {
                    "genres": [],
                    "year_range": [1990, datetime.now().year],
                    "min_rating": 6.0,
                    "mood": None
                },
                "selected_mood_names": []  # Added for mood filter compatibility
            })
    
    def _load_user_profile(self) -> Dict[str, Any]:
        """Load or create user profile"""
        try:
            if USER_PROFILES_PATH.exists():
                with open(USER_PROFILES_PATH, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {
                        "user_id": str(datetime.now().timestamp()),
                        "preferences": {},
                        "activity": {}
                    }
        except Exception as e:
            st.error(f"Error loading user profile: {e}")
        
        return {
            "user_id": str(datetime.now().timestamp()),
            "preferences": {
                "theme": "dark",
                "font_size": "medium",
                "critic_mode": "default"
            },
            "activity": {
                "first_visit": datetime.now().isoformat(),
                "last_visit": datetime.now().isoformat(),
                "movies_viewed": 0
            }
        }
    
    def _load_watchlist(self) -> Dict[str, Any]:
        """Load watchlist from file"""
        watchlist_path = Path("static_data/watchlist.json")
        try:
            if watchlist_path.exists():
                with open(watchlist_path, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {"movies": data, "last_updated": None}
        except Exception as e:
            st.error(f"Error loading watchlist: {e}")
        
        return {"movies": [], "last_updated": None}

    # ------------ DATA LOADING METHODS (for filters) ------------
    
    @staticmethod
    def load_genres() -> List[Dict[str, Any]]:
        """Load movie genres from static file"""
        try:
            if GENRES_PATH.exists():
                with open(GENRES_PATH, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else data.get("genres", [])
        except Exception as e:
            st.error(f"Error loading genres: {e}")
        return [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 35, "name": "Comedy"}
        ]
    
    @staticmethod
    def load_moods() -> List[Dict[str, Any]]:
        """Load mood options from static file"""
        try:
            if MOODS_PATH.exists():
                with open(MOODS_PATH, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else data.get("moods", [])
        except Exception as e:
            st.error(f"Error loading moods: {e}")
        return [
            {"id": 1, "name": "Happy", "emoji": "😊"},
            {"id": 2, "name": "Sad", "emoji": "😢"}
        ]
    
    def get_starter_packs(self) -> Dict[str, Any]:
        """Load available starter packs"""
        try:
            if STARTER_PACKS_PATH.exists():
                with open(STARTER_PACKS_PATH, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {"packs": data}
        except Exception as e:
            st.error(f"Error loading starter packs: {e}")
        return {}

    # ------------ STATE MANAGEMENT METHODS ------------
    
    def save_state(self) -> None:
        """Persist critical session data to disk"""
        try:
            # Save user profile
            with open(USER_PROFILES_PATH, "w") as f:
                json.dump(st.session_state.user_profile, f, indent=2)
                
            # Save watchlist
            with open("static_data/watchlist.json", "w") as f:
                json.dump(st.session_state.watchlist, f, indent=2)
                
        except Exception as e:
            st.error(f"Error saving session state: {e}")

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        st.session_state.last_activity = datetime.now().isoformat()
        st.session_state.user_profile["activity"]["last_visit"] = st.session_state.last_activity
    
    def set_starter_pack(self, pack_id: str) -> None:
        """Set the active starter pack and update user profile"""
        packs = self.get_starter_packs()
        if pack_id in packs:
            st.session_state.starter_pack = pack_id
            st.session_state.user_profile.update({
                "starter_pack": pack_id,
                "starter_pack_selected_at": datetime.now().isoformat()
            })
            self.save_state()
    
    def get_active_filters(self) -> Dict[str, Any]:
        """Return current filter state"""
        return st.session_state.active_filters
    
    def update_filter(self, filter_type: str, value: Any) -> None:
        """Update a specific filter type"""
        if filter_type in st.session_state.active_filters:
            st.session_state.active_filters[filter_type] = value
            self.update_activity()

# Create module-level functions for backward compatibility
def load_genres() -> List[Dict[str, Any]]:
    return SessionHelper.load_genres()

def load_moods() -> List[Dict[str, Any]]:
    return SessionHelper.load_moods()

# Singleton pattern for session helper
@st.cache_resource
def get_session_helper() -> SessionHelper:
    return SessionHelper()