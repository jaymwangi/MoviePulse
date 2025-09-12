"""
Core Data Models for MoviePulse
-------------------------------
Defines fundamental data structures used across the application.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from enum import Enum
from pathlib import Path

# Recommendation system constants
RECOMMENDER_DATA_DIR = Path(__file__).parent.parent / "static_data"
RECOMMENDER_DATA_DIR.mkdir(parents=True, exist_ok=True)

GENRES_MAP_FILE = RECOMMENDER_DATA_DIR / "genres_map.json"
MOODS_MAP_FILE = RECOMMENDER_DATA_DIR / "moods_map.json"
EMBEDDINGS_FILE = RECOMMENDER_DATA_DIR / "embeddings.pkl"
ACTOR_SIMILARITY_FILE = RECOMMENDER_DATA_DIR / "actor_similarity.json"
GENRE_MAPPINGS_FILE = RECOMMENDER_DATA_DIR / "genre_mappings.json"
MOOD_GENRE_MAPPINGS = RECOMMENDER_DATA_DIR / "mood_genre_mappings.json"
USER_PREFERENCES_FILE = RECOMMENDER_DATA_DIR / "user_preferences.json"
GENRES_FILE = RECOMMENDER_DATA_DIR / "genres.json"
MOODS_FILE = RECOMMENDER_DATA_DIR / "moods.json"

# Logging configuration
USER_PREFS_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | user=%(user_id)s | "
    "top_genres=%(genres)s | strength=%(strength).2f | "
    "source=%(source)s"
)

# TMDB image URLs
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_POSTER_PLACEHOLDER = "/placeholder_poster.jpg"

@dataclass
class Genre:
    id: int
    name: str
    tmdb_id: Optional[int] = None  # Additional API reference

    def __post_init__(self):
        if self.tmdb_id is None:
            self.tmdb_id = self.id

@dataclass
class Person:
    id: int
    name: str
    role: str  # "actor", "director", etc.
    profile_path: Optional[str] = None
    known_for_department: Optional[str] = None

@dataclass
class Movie:
    id: int
    title: str
    overview: str
    release_date: str  # Format: "YYYY-MM-DD"
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    genres: List[Genre] = field(default_factory=list)
    cast: List[Person] = field(default_factory=list)
    directors: List[Person] = field(default_factory=list)
    runtime: Optional[int] = None
    similar_movies: Optional[List[int]] = field(default_factory=list)

    @property
    def year(self) -> Optional[int]:
        try:
            return int(self.release_date[:4]) if self.release_date else None
        except (ValueError, TypeError):
            return None

@dataclass
class Video:
    key: str
    type: str
    site: str

# Theme and styling constants
THEME_OPTIONS = ["dark", "light", "system"]
FONT_OPTIONS = ["default", "dyslexia", "large"]
CRITIC_MODE_OPTIONS = ["balanced", "strict", "lenient", "arthouse", "blockbuster", "indie", "default"]

# Accessibility options
FONT_OPTIONS = ["default", "dyslexia-friendly", "large-text"]
HIGH_CONTRAST_OPTIONS = [False, True]
SPOILER_FREE_OPTIONS = [False, True]
DYSLEXIA_MODE_OPTIONS = [False, True]

# CSS classes for theme-aware styling
THEME_CSS_CLASSES = {
    "primary": "custom-primary",
    "secondary": "custom-secondary",
    "bg": "custom-bg",
    "text": "custom-text",
    "border": "custom-border",
    "card": "theme-aware-card"
}

# Path constants for theme assets
THEME_ASSETS_DIR = Path(__file__).parent.parent / "media_assets" / "styles"
DARK_THEME_CSS = THEME_ASSETS_DIR / "theme_dark.css"
LIGHT_THEME_CSS = THEME_ASSETS_DIR / "theme_light.css"
ACCESSIBILITY_CSS = THEME_ASSETS_DIR / "accessibility.css"

# Ensure theme directories exist
THEME_ASSETS_DIR.mkdir(parents=True, exist_ok=True)