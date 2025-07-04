import json
from pathlib import Path
from typing import Dict, Any
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
