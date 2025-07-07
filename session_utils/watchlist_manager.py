import json
import streamlit as st
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# Constants
WATCHLIST_PATH = Path("static_data/watchlist.json")
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "watchlist.log"

# Setup rotating logs
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("watchlist_logger")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=5
)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def ensure_watchlist():
    """Ensure session watchlist is initialized"""
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

def load_watchlist() -> dict:
    """Load watchlist from JSON with empty dict fallback"""
    try:
        return json.loads(WATCHLIST_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def persist_watchlist() -> bool:
    """Save current session watchlist to JSON"""
    WATCHLIST_PATH.parent.mkdir(exist_ok=True)
    user_id = st.session_state.get("user_id", "anonymous")
    
    all_data = load_watchlist()
    all_data[user_id] = {
        "movies": st.session_state.watchlist,
        "timestamp": str(datetime.now())
    }
    
    WATCHLIST_PATH.write_text(json.dumps(all_data, indent=2))
    logger.info(f"Watchlist persisted for user {user_id}")
    return True

def add_to_watchlist(movie_data: dict):
    """Enhanced version to handle starter packs"""
    user_id = st.session_state.get("user_id", "anonymous")
    watchlist_data = load_watchlist()
    
    if user_id not in watchlist_data:
        watchlist_data[user_id] = {"movies": []}
    
    # Skip if movie already exists
    if any(m["movie_id"] == movie_data["movie_id"] for m in watchlist_data[user_id]["movies"]):
        return False
    
    # Fetch basic details if missing (for starter packs)
    if not movie_data.get("title"):
        try:
            from service_clients.tmdb_client import tmdb_client
            details = tmdb_client.get_movie_details(movie_data["movie_id"])
            movie_data.update({
                "title": details.get("title", "Unknown"),
                "poster_path": details.get("poster_path", ""),
                "year": details.get("release_date", "")[:4] if details.get("release_date") else ""
            })
        except Exception as e:
            logger.warning(f"Couldn't fetch details for movie {movie_data['movie_id']}: {str(e)}")
            movie_data.update({
                "title": f"Movie {movie_data['movie_id']}",
                "poster_path": "",
                "year": ""
            })
    
    watchlist_data[user_id]["movies"].append(movie_data)
    WATCHLIST_PATH.write_text(json.dumps(watchlist_data, indent=2))
    st.session_state.watchlist = watchlist_data[user_id]["movies"]
    return True

def remove_from_watchlist(movie_id: int):
    """Remove movie by ID from watchlist"""
    user_id = st.session_state.get("user_id", "anonymous")
    watchlist_data = load_watchlist()
    
    if user_id in watchlist_data:
        initial_count = len(watchlist_data[user_id]["movies"])
        watchlist_data[user_id]["movies"] = [
            m for m in watchlist_data[user_id]["movies"]
            if m["movie_id"] != movie_id
        ]
        
        if len(watchlist_data[user_id]["movies"]) < initial_count:
            WATCHLIST_PATH.write_text(json.dumps(watchlist_data, indent=2))
            st.session_state.watchlist = watchlist_data[user_id]["movies"]
            return True
    return False
def get_user_watchlist(user_id: str = None) -> list:
    """Get watchlist for specific user"""
    user_id = user_id or st.session_state.get("user_id", "anonymous")
    return load_watchlist().get(user_id, {}).get("movies", [])