# session_utils/user_profile.py
import json
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

# Constants
PROFILE_FILE = "user_profiles.json"
PACK_TO_GENRE_FILE = "static_data/pack_to_genre_map.json"
DEFAULT_PROFILE = {
    "critic_mode": "default",
    "theme": "dark",
    "watchlist": [],
    "view_history": [],
    "starter_pack": None,
    "preferences": {}
}

def _ensure_profile_file():
    """Create profile file if it doesn't exist"""
    if not Path(PROFILE_FILE).exists():
        with open(PROFILE_FILE, 'w') as f:
            json.dump({}, f)

def get_user_id() -> str:
    """Get or create a session-based user identifier"""
    if "user_id" not in st.session_state:
        # Create a random ID for this session
        st.session_state.user_id = "session_" + str(uuid.uuid4())[:8]
    return st.session_state.user_id

def load_current_profile() -> Dict[str, Any]:
    """Load the current user's profile"""
    _ensure_profile_file()
    user_id = get_user_id()
    
    try:
        with open(PROFILE_FILE, 'r') as f:
            all_profiles = json.load(f)
            profile = all_profiles.get(user_id, DEFAULT_PROFILE.copy())
            # Ensure all default fields exist in loaded profile
            for key, value in DEFAULT_PROFILE.items():
                if key not in profile:
                    profile[key] = value
            return profile
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_PROFILE.copy()

def save_profile(profile: Dict[str, Any]):
    """Save the user profile"""
    _ensure_profile_file()
    user_id = get_user_id()
    
    try:
        with open(PROFILE_FILE, 'r') as f:
            all_profiles = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        all_profiles = {}
    
    all_profiles[user_id] = profile
    
    with open(PROFILE_FILE, 'w') as f:
        json.dump(all_profiles, f, indent=2)

def set_critic_mode(mode: str):
    """Set and persist the critic mode"""
    profile = load_current_profile()
    profile["critic_mode"] = mode
    save_profile(profile)
    st.session_state.critic_mode = mode  # Keep in sync with session

def get_critic_mode() -> str:
    """Get the current critic mode"""
    if "critic_mode" not in st.session_state:
        profile = load_current_profile()
        st.session_state.critic_mode = profile.get("critic_mode", "default")
    return st.session_state.critic_mode

def set_starter_pack(pack_name: str):
    """Set and persist the user's starter pack selection"""
    profile = load_current_profile()
    profile["starter_pack"] = pack_name
    
    # Update genre preferences based on pack selection
    try:
        with open(PACK_TO_GENRE_FILE, 'r') as f:
            pack_to_genre = json.load(f)
        
        if pack_name in pack_to_genre:
            genre = pack_to_genre[pack_name]
            profile["preferences"][genre] = profile["preferences"].get(genre, 0) + 1
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # Skip genre update if mapping file not available
    
    save_profile(profile)
    st.session_state.starter_pack = pack_name

def get_starter_pack() -> Optional[str]:
    """Get the user's selected starter pack"""
    if "starter_pack" not in st.session_state:
        profile = load_current_profile()
        st.session_state.starter_pack = profile.get("starter_pack")
    return st.session_state.starter_pack

def get_user_preferences() -> Dict[str, int]:
    """Get the user's genre preferences"""
    profile = load_current_profile()
    return profile.get("preferences", {})

def init_profile():
    """Initialize profile if not already loaded"""
    if "profile_initialized" not in st.session_state:
        get_critic_mode()  # Load profile
        get_starter_pack()  # Load starter pack
        st.session_state.profile_initialized = True