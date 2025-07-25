# session_utils/user_profile.py
import json
import logging
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import uuid
from datetime import datetime

# Constants
PROFILE_FILE = "user_profiles.json"
PACK_TO_GENRE_FILE = "static_data/pack_to_genre_map.json"
BADGES_CONFIG = "static_data/cinephile_badges.json"
DEFAULT_PROFILE = {
    "critic_mode": "default",
    "theme": "dark",
    "watchlist": [],
    "view_history": [],
    "starter_pack": None,
    "preferences": {},
    "selected_moods": [],
    "badge_progress": {},
    "earned_badges": []
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _ensure_profile_file():
    """Create profile file if it doesn't exist with proper permissions"""
    try:
        if not Path(PROFILE_FILE).exists():
            with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to create profile file: {str(e)}")
        raise

def _load_json_file(file_path: str) -> Dict[str, Any]:
    """Generic JSON file loader with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {file_path} with utf-8-sig: {str(e)}")
            return {}
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}")
        return {}

def _load_badges_config() -> Dict[str, Any]:
    """Load the badge configuration with proper encoding and validation"""
    config = _load_json_file(BADGES_CONFIG)
    if not config:
        config = {"badges": [], "tracking_fields": {}}
    
    # Validate badge structure
    valid_badges = []
    for badge in config.get("badges", []):
        if not all(key in badge for key in ["id", "name", "threshold", "tracking_field"]):
            logger.warning(f"Skipping invalid badge: {badge.get('id', 'unknown')}")
            continue
        valid_badges.append(badge)
    
    config["badges"] = valid_badges
    return config

def get_user_id() -> str:
    """Get or create a session-based user identifier"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = "session_" + str(uuid.uuid4())[:8]
        logger.info(f"Generated new user ID: {st.session_state.user_id}")
    return st.session_state.user_id

def load_current_profile() -> Dict[str, Any]:
    """Load the current user's profile with validation and defaults"""
    _ensure_profile_file()
    user_id = get_user_id()
    
    try:
        with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
            all_profiles = json.load(f)
            profile = all_profiles.get(user_id, DEFAULT_PROFILE.copy())
    except Exception as e:
        logger.error(f"Failed to load profiles: {str(e)}")
        profile = DEFAULT_PROFILE.copy()
    
    # Ensure all default fields exist with proper types
    for key, default_value in DEFAULT_PROFILE.items():
        if key not in profile:
            profile[key] = default_value.copy() if hasattr(default_value, 'copy') else default_value
        elif isinstance(default_value, dict) and isinstance(profile[key], dict):
            # Merge dictionaries to preserve existing values while adding new defaults
            profile[key] = {**default_value, **profile[key]}
    
    return profile

def save_profile(profile: Dict[str, Any]):
    """Save the user profile with validation and error handling"""
    _ensure_profile_file()
    user_id = get_user_id()
    
    try:
        # Load all profiles first to preserve other users' data
        with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
            all_profiles = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load existing profiles: {str(e)}")
        all_profiles = {}
    
    # Validate profile structure before saving
    validated_profile = {}
    for key, default_value in DEFAULT_PROFILE.items():
        if key in profile:
            # Ensure the saved value matches the expected type
            if isinstance(default_value, type(profile[key])):
                validated_profile[key] = profile[key]
            else:
                logger.warning(f"Type mismatch for {key}, using default")
                validated_profile[key] = default_value.copy() if hasattr(default_value, 'copy') else default_value
        else:
            validated_profile[key] = default_value.copy() if hasattr(default_value, 'copy') else default_value
    
    all_profiles[user_id] = validated_profile
    
    try:
        with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_profiles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save profile: {str(e)}")
        raise

def _matches_filter(view_entry: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
    """
    Check if a view entry matches the given filter criteria.
    Supports special operators: $not, $gt, $lt, $in, $nin
    """
    for field, condition in filter_criteria.items():
        if field == "$not":
            # Handle $not operator - expect condition to be {field: value}
            if not isinstance(condition, dict):
                return False
            for subfield, value in condition.items():
                if view_entry.get(subfield) == value:
                    return False
        elif isinstance(condition, dict) and "$not" in condition:
            # Handle field: {"$not": value} case
            if view_entry.get(field) == condition["$not"]:
                return False
        elif field.startswith("$"):
            # Handle other operators if needed
            pass
        else:
            # Direct equality comparison
            if view_entry.get(field) != condition:
                return False
    return True

def record_movie_view(movie_data: Dict[str, Any]):
    """
    Record a movie view and update badge progress accordingly.
    """
    if not movie_data.get("id"):
        logger.error("Attempted to record movie view without ID")
        return
    
    profile = load_current_profile()
    badges_config = _load_badges_config()
    
    # Create view entry with timestamp and normalized data
    view_entry = {
        "movie_id": movie_data["id"],
        "timestamp": datetime.now().isoformat(),
        "is_criterion": movie_data.get("is_criterion", False),
        "original_language": movie_data.get("original_language", "en").lower(),
        "critic_score": round(movie_data.get("vote_average", 0) * 10, 1),
        "director_ids": movie_data.get("director_ids", []),
        "genres": movie_data.get("genres", []),
        "year": movie_data.get("year")
    }
    
    # Update view history (limit to 100 most recent)
    current_history = profile.get("view_history", [])
    
    # Add new entry at the beginning (most recent first)
    current_history.insert(0, view_entry)
    
    # Trim to exactly 100 entries if needed
    if len(current_history) > 100:
        current_history = current_history[:100]
    
    profile["view_history"] = current_history
    
    # Initialize badge progress if missing
    if "badge_progress" not in profile:
        profile["badge_progress"] = {}
    
    # Update progress for each tracking field
    for field, config in badges_config.get("tracking_fields", {}).items():
        if config["source"] == "watch_history":
            if _matches_filter(view_entry, config.get("filter", {})):
                current = profile["badge_progress"].get(field, 0)
                profile["badge_progress"][field] = current + 1
    
    # Special handling for director-specific tracking
    if "director_completions" in badges_config.get("tracking_fields", {}):
        for director_id in view_entry.get("director_ids", []):
            key = f"director_{director_id}"
            current = profile["badge_progress"].get(key, 0)
            profile["badge_progress"][key] = current + 1
    
    # Check for newly earned badges
    _check_new_badges(profile, badges_config)
    
    save_profile(profile)
    logger.info(f"Recorded view for movie {movie_data['id']}")
    
def _check_new_badges(profile: Dict[str, Any], badges_config: Dict[str, Any]):
    """
    Internal function to check and award new badges based on updated progress
    """
    earned_badges = set(profile.get("earned_badges", []))
    new_badges = []
    
    for badge in badges_config.get("badges", []):
        if badge["id"] in earned_badges:
            continue
        
        tracking_field = badge["tracking_field"]
        threshold = badge["threshold"]
        
        if badge.get("composite", False):
            # Composite badge - check required components
            component_ids = badge.get("requirements", [])
            if all(cid in earned_badges for cid in component_ids):
                new_badges.append(badge["id"])
        elif tracking_field == "director_completions":
            # Director badge - check any director meets threshold
            for key, progress in profile["badge_progress"].items():
                if key.startswith("director_") and progress >= threshold:
                    new_badges.append(badge["id"])
                    break
        else:
            # Regular badge - check progress
            current = profile["badge_progress"].get(tracking_field, 0)
            if current >= threshold:
                new_badges.append(badge["id"])
    
    if new_badges:
        profile["earned_badges"] = list(earned_badges.union(new_badges))
        st.session_state.new_badges = new_badges
        logger.info(f"Awarded new badges: {', '.join(new_badges)}")

def get_badge_progress() -> Dict[str, Tuple[int, int]]:
    """
    Get current progress for all badges.
    
    Returns:
        Dictionary mapping badge IDs to tuples of (current_progress, threshold)
    """
    profile = load_current_profile()
    badges_config = _load_badges_config()
    progress = {}
    
    for badge in badges_config.get("badges", []):
        badge_id = badge["id"]
        
        if badge.get("composite", False):
            # Composite badge progress shows components earned
            component_ids = badge.get("requirements", [])
            earned = sum(1 for cid in component_ids if cid in profile.get("earned_badges", []))
            progress[badge_id] = (earned, len(component_ids))
        else:
            tracking_field = badge["tracking_field"]
            threshold = badge["threshold"]
            
            if tracking_field == "director_completions":
                # For director badges, show max progress across all directors
                max_progress = max(
                    (p for k, p in profile.get("badge_progress", {}).items() 
                     if k.startswith("director_")),
                    default=0
                )
                progress[badge_id] = (max_progress, threshold)
            else:
                current = profile.get("badge_progress", {}).get(tracking_field, 0)
                progress[badge_id] = (current, threshold)
    
    return progress

def get_earned_badges() -> List[Dict[str, Any]]:
    """Get metadata for all earned badges"""
    profile = load_current_profile()
    badges_config = _load_badges_config()
    
    return [
        badge for badge in badges_config.get("badges", [])
        if badge["id"] in profile.get("earned_badges", [])
    ]

def clear_new_badges_notification():
    """Clear any new badge notifications from the session state"""
    if "new_badges" in st.session_state:
        del st.session_state["new_badges"]

# ===== Profile Management Functions =====
def set_critic_mode(mode: str):
    """Set and persist the critic mode preference"""
    if mode not in ["default", "strict", "lenient"]:
        logger.warning(f"Attempt to set invalid critic mode: {mode}")
        return
    
    profile = load_current_profile()
    profile["critic_mode"] = mode
    save_profile(profile)
    st.session_state.critic_mode = mode
    logger.info(f"Set critic mode to: {mode}")

def get_critic_mode() -> str:
    """Get the current critic mode preference"""
    if "critic_mode" not in st.session_state:
        profile = load_current_profile()
        st.session_state.critic_mode = profile.get("critic_mode", "default")
    return st.session_state.critic_mode

def set_starter_pack(pack_name: str):
    """Set and persist the user's starter pack selection"""
    profile = load_current_profile()
    profile["starter_pack"] = pack_name
    
    # Update genre preferences based on starter pack
    pack_to_genre = _load_json_file(PACK_TO_GENRE_FILE)
    if pack_name in pack_to_genre:
        genre = pack_to_genre[pack_name]
        profile["preferences"][genre] = profile["preferences"].get(genre, 0) + 1
    
    save_profile(profile)
    st.session_state.starter_pack = pack_name
    logger.info(f"Set starter pack to: {pack_name}")

def get_starter_pack() -> Optional[str]:
    """Get the user's selected starter pack"""
    if "starter_pack" not in st.session_state:
        profile = load_current_profile()
        st.session_state.starter_pack = profile.get("starter_pack")
    return st.session_state.starter_pack

def get_user_preferences() -> Dict[str, int]:
    """Get the user's genre preferences with validation"""
    profile = load_current_profile()
    prefs = profile.get("preferences", {})
    return {k: v for k, v in prefs.items() if isinstance(v, int)}

def update_preference(genre: str, delta: int = 1):
    """Update a genre preference by the given delta"""
    profile = load_current_profile()
    current = profile["preferences"].get(genre, 0)
    profile["preferences"][genre] = max(0, current + delta)
    save_profile(profile)
    logger.info(f"Updated {genre} preference by {delta}")

def set_selected_moods(moods: List[str]):
    """Set and persist the user's selected moods"""
    profile = load_current_profile()
    profile["selected_moods"] = moods
    save_profile(profile)
    st.session_state.selected_moods = moods.copy()
    logger.info(f"Set moods to: {', '.join(moods)}")

def get_selected_moods() -> List[str]:
    """Get the user's current mood selections"""
    if "selected_moods" not in st.session_state:
        profile = load_current_profile()
        st.session_state.selected_moods = profile.get("selected_moods", []).copy()
    return st.session_state.selected_moods.copy()

def clear_selected_moods():
    """Clear all mood selections"""
    set_selected_moods([])

def add_selected_mood(mood: str):
    """Add a single mood to selections if not already present"""
    current_moods = get_selected_moods()
    if mood not in current_moods:
        set_selected_moods(current_moods + [mood])

def remove_selected_mood(mood: str):
    """Remove a specific mood from selections"""
    current_moods = get_selected_moods()
    if mood in current_moods:
        set_selected_moods([m for m in current_moods if m != mood])

def init_profile():
    """Initialize profile if not already loaded"""
    if "profile_initialized" not in st.session_state:
        get_critic_mode()
        get_starter_pack()
        get_selected_moods()
        st.session_state.profile_initialized = True
        logger.info("Profile initialized")

def update_cinephile_stats(movie_id: int):
    """Update cinephile stats when viewing a movie"""
    from service_clients.tmdb_client import tmdb_client
    
    # Basic movie data fallback
    movie_data = {
        "id": movie_id,
        "is_criterion": False,
        "original_language": "en",
        "vote_average": 0,
        "director_ids": [],
        "genres": [],
        "year": None
    }
    
    if tmdb_client:
        try:
            # Get enhanced movie details from TMDB
            movie = tmdb_client.get_movie_details(movie_id)
            if movie:
                movie_data.update({
                    "is_criterion": hasattr(movie, 'belongs_to_collection') and bool(movie.belongs_to_collection),
                    "original_language": getattr(movie, 'original_language', 'en'),
                    "vote_average": getattr(movie, 'vote_average', 0),
                    "director_ids": [director.id for director in getattr(movie, 'directors', [])],
                    "genres": [genre.id for genre in getattr(movie, 'genres', [])],
                    "year": int(getattr(movie, 'release_date', '')[:4]) if hasattr(movie, 'release_date') else None
                })
        except Exception as e:
            logger.warning(f"Couldn't fetch full movie details: {str(e)}")
    
    try:
        record_movie_view(movie_data)
    except Exception as e:
        logger.error(f"Failed to record movie view: {str(e)}")
        st.error("Failed to update viewing statistics")

# ===== Watchlist Functions =====
def add_to_watchlist(movie_id: int, movie_title: str):
    """Add a movie to the user's watchlist"""
    profile = load_current_profile()
    watchlist = profile.get("watchlist", [])
    
    if not any(m["id"] == movie_id for m in watchlist):
        watchlist.append({
            "id": movie_id,
            "title": movie_title,
            "added": datetime.now().isoformat()
        })
        profile["watchlist"] = watchlist
        save_profile(profile)
        logger.info(f"Added movie {movie_id} to watchlist")

def remove_from_watchlist(movie_id: int):
    """Remove a movie from the user's watchlist"""
    profile = load_current_profile()
    profile["watchlist"] = [m for m in profile.get("watchlist", []) if m["id"] != movie_id]
    save_profile(profile)
    logger.info(f"Removed movie {movie_id} from watchlist")

def get_watchlist() -> List[Dict[str, Any]]:
    """Get the user's current watchlist"""
    profile = load_current_profile()
    return profile.get("watchlist", []).copy()

def is_in_watchlist(movie_id: int) -> bool:
    """Check if a movie is in the user's watchlist"""
    return any(m["id"] == movie_id for m in get_watchlist())