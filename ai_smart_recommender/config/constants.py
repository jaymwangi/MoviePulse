from pathlib import Path
from enum import Enum, auto

# Path Constants
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'static_data'
LOG_DIR = DATA_DIR / 'logs'

# Recommendation Constants
DEFAULT_REC_LIMIT = 10
FALLBACK_THRESHOLD = 0.4
MIN_SIMILARITY = 0.3

# File Paths
EMBEDDINGS_FILE = DATA_DIR / 'embeddings.pkl'
GENRE_MAPPINGS_FILE = DATA_DIR / 'genre_mappings.json'
ACTOR_SIMILARITY_FILE = DATA_DIR / 'actor_similarity.json'
STARTER_PACKS_FILE = DATA_DIR / 'starter_packs.json'
PACK_GENRE_MAP_FILE = DATA_DIR / 'pack_genres.json'  # updated filename
ANALYTICS_LOG_PATH = LOG_DIR / 'recommendation_analytics.log'

# TMDB Config
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

class Strategy(Enum):
    """Enumeration of all recommendation strategies in the system."""
    CONTENT_BASED = auto()
    GENRE_BASED = auto()
    MOOD_BASED = auto()
    ACTOR_BASED = auto()
    POPULARITY_FALLBACK = auto()
    GENRE_FALLBACK = auto()
    MOOD_FALLBACK = auto()
    ACTOR_FALLBACK = auto()
    CURATED_FALLBACK = auto()

    @property
    def display_name(self) -> str:
        return {
            Strategy.CONTENT_BASED: "Content-Based",
            Strategy.GENRE_BASED: "Genre-Based",
            Strategy.MOOD_BASED: "Mood-Based",
            Strategy.ACTOR_BASED: "Actor-Based",
            Strategy.POPULARITY_FALLBACK: "Popularity Fallback",
            Strategy.GENRE_FALLBACK: "Genre Fallback",
            Strategy.MOOD_FALLBACK: "Mood Fallback",
            Strategy.ACTOR_FALLBACK: "Actor Fallback",
            Strategy.CURATED_FALLBACK: "Curated Fallback",
        }[self]

class FallbackPriority(Enum):
    """Execution priority order for fallback strategies. Lower = higher priority."""
    GENRE = 1
    MOOD = 2
    ACTOR = 3
    POPULARITY = 4
    CURATED = 5
