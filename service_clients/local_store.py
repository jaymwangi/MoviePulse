import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any,Tuple,List
import logging
from logging.handlers import RotatingFileHandler

# =========================
# LOGGING SETUP
# =========================

# Ensure logs directory exists at root
logs_path = Path("logs")
logs_path.mkdir(exist_ok=True)

# Rotating file handler (1 MB max, 5 backups)
file_handler = RotatingFileHandler(
    logs_path / "user_prefs.log",
    maxBytes=1024 * 1024,  # 1 MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
))

# Combine handlers into logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =========================
# FUNCTIONALITY
# =========================

def load_user_preferences() -> Dict[str, Any]:
    """Load user preferences from JSON file"""
    prefs_path = Path("user_data/preferences.json")
    try:
        if prefs_path.exists():
            logger.info(f"Loading user preferences from {prefs_path}")
            with open(prefs_path, 'r') as f:
                data = json.load(f)
                logger.debug(f"Loaded preferences: {data}")
                return data
        else:
            logger.info(f"No preferences file found at {prefs_path}, returning empty preferences.")
            return {}
    except Exception as e:
        logger.error(f"Failed to load user preferences from {prefs_path}: {e}")
        return {}

def save_user_preferences(user_id: str, preferences: Dict[str, Any]):
    """Save user preferences to JSON file"""
    prefs_path = Path("user_data/preferences.json")
    try:
        logger.info(f"Saving preferences for user {user_id}")
        prefs_path.parent.mkdir(exist_ok=True)
        
        all_prefs = load_user_preferences()
        all_prefs[user_id] = preferences
        
        with open(prefs_path, 'w') as f:
            json.dump(all_prefs, f, indent=2)
        
        logger.info(f"Preferences for user {user_id} saved successfully to {prefs_path}")
    except Exception as e:
        logger.error(f"Failed to save user preferences to {prefs_path}: {e}")

def load_embeddings_with_ids(path: Path = Path("static_data/embeddings.pkl")) -> Tuple[np.ndarray, List[int]]:
    """
    Load embeddings and movie IDs from disk, returning them as a tuple (embeddings, ids)
    Expects the file to contain a tuple: (np.ndarray, List[int])
    """
    try:
        if not path.exists():
            logger.warning(f"Embeddings file not found at {path}")
            return np.array([]), []

        with path.open("rb") as f:
            data = pickle.load(f)

        if not isinstance(data, tuple) or len(data) != 2:
            raise ValueError("Embeddings file must contain a tuple: (ndarray, list[int])")

        embeddings, ids = data

        if not isinstance(embeddings, np.ndarray) or not isinstance(ids, list):
            raise ValueError("Invalid data types inside the embeddings tuple")

        logger.info(f"Loaded {len(ids)} embeddings from {path}")
        return embeddings, ids

    except Exception as e:
        logger.error(f"Failed to load embeddings from {path}: {e}")
        return np.array([]), []
    
def load_genre_mappings(path: Path = Path("static_data/genres.json")) -> Dict[int, str]:
    try:
        logger.info(f"Loading genre mappings from {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        genre_map = {item["id"]: item["name"] for item in raw if "id" in item and "name" in item}
        return genre_map

    except Exception as e:
        logger.error(f"Failed to load genre mappings: {e}")
        return {}

def load_mood_genre_map(
    path: Path = Path("static_data/mood_genre_mappings.json")
) -> Dict[str, Dict[str, Any]]:
    """
    Loads the full mood-to-genre mapping including:
    - genres (List[int])
    - weight (float)
    - description (str)
    """
    try:
        logger.info(f"Loading mood-genre map from {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load mood-genre map: {e}")
        return {}
    
def load_actor_similarity(path: Path = Path("static_data/actor_similarity.json")) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load actor similarity data: {e}")
        return {}
