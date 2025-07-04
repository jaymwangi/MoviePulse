# dev_scripts/ingest_genre_data.py
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/genre_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment setup
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Imports
from service_clients.tmdb_client import tmdb_client
from core_config import constants

def fetch_and_cache_genre_data():
    """Enhanced version that handles both basic genres and recommender mappings"""
    logger.info("Starting genre data ingestion and caching process")
    
    try:
        # 1. Get basic genre list
        logger.info("Fetching genre list from TMDB...")
        genres = tmdb_client.get_genres()
        genre_map = {str(g.id): g.name for g in genres}
        logger.info(f"Retrieved {len(genres)} genres")
        
        # 2. Save basic genre definitions
        basic_genres_path = constants.RECOMMENDER_DATA_DIR / "genres.json"
        with basic_genres_path.open("w", encoding="utf-8") as f:
            json.dump([g.__dict__ for g in genres], f, indent=2, ensure_ascii=False)
        logger.info(f"Saved genre definitions to {basic_genres_path}")
        
        # 3. Build comprehensive mappings for recommender
        logger.info("Building movie-genre mappings for recommendations...")
        movie_genres = {}
        
        # Get trending movies - using your actual API method signature
        movies, total_pages = tmdb_client.get_trending_movies()
        
        # Process all available pages (adjust if needed)
        for page in tqdm(range(1, min(total_pages, 5) + 1), desc="Fetching pages"):
            if page > 1:  # Already got page 1 above
                movies, _ = tmdb_client.get_trending_movies(page=page)
            
            for movie in movies:
                movie_genres[str(movie.id)] = {
                    "genre_ids": [str(g.id) for g in movie.genres],
                    "title": movie.title
                }
        
        # 4. Save recommender-ready data
        mappings_path = constants.RECOMMENDER_DATA_DIR / "genre_mappings.json"
        with mappings_path.open("w", encoding="utf-8") as f:
            json.dump({
                "version": "1.1",
                "last_updated": datetime.now().isoformat(),
                "genre_definitions": genre_map,
                "movie_genres": movie_genres,
                "stats": {
                    "total_genres": len(genre_map),
                    "total_movies": len(movie_genres)
                }
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"""
        Successfully cached:
        - {len(genre_map)} genre definitions (genres.json)
        - {len(movie_genres)} movie mappings (genre_mappings.json)
        """)
        
    except Exception as e:
        logger.error(f"An error occurred during genre data ingestion: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    constants.RECOMMENDER_DATA_DIR.mkdir(exist_ok=True)
    fetch_and_cache_genre_data()