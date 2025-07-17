from pathlib import Path
import os

# Path Constants
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'static_data'

# Recommendation Constants
DEFAULT_REC_LIMIT = 10
FALLBACK_THRESHOLD = 0.4
MIN_SIMILARITY = 0.3

# File Paths
EMBEDDINGS_FILE = DATA_DIR / 'embeddings.pkl'
GENRE_MAPPINGS_FILE = DATA_DIR / 'genre_mappings.json'

# TMDB Config
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
