"""
Precompute Embeddings Script
----------------------------
Orchestrates the process of:
1. Loading movie metadata from JSON
2. Generating embeddings using MovieEmbeddingEngine
3. Building a FAISS index with VectorDB
4. Saving embeddings and index to disk
"""

import json
import pickle
import time
import logging
from pathlib import Path
from typing import Tuple
import numpy as np
from ai_smart_recommender.recommender_engine.core_logic.embedding_engine import MovieEmbeddingEngine
from ai_smart_recommender.recommender_engine.core_logic.vector_db import VectorDB

# Setup logging - now with both file and console output
LOG_FILE = Path("logs/embedding_perf.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Path configuration
MOVIE_JSON = Path("static_data/movies.json")
EMBEDDINGS_PKL = Path("static_data/embeddings.pkl")
FAISS_INDEX = Path("static_data/vector_index.faiss")

def load_movies() -> list:
    """Load movie data from JSON file."""
    if not MOVIE_JSON.exists():
        raise FileNotFoundError(f"Movie data file not found at {MOVIE_JSON}")
    
    logger.info(f"Loading movies from {MOVIE_JSON}")
    with MOVIE_JSON.open(encoding="utf-8") as f:
        movies = json.load(f)
    
    if not isinstance(movies, list):
        raise ValueError("Movie data should be a list of movie objects")
    
    logger.info(f"Successfully loaded {len(movies)} movies")
    return movies

def generate_embeddings(movies: list) -> Tuple[np.ndarray, list]:
    """Generate embeddings for all movies."""
    logger.info("Initializing embedding engine")
    engine = MovieEmbeddingEngine()
    
    logger.info("Generating movie embeddings...")
    start_time = time.time()
    embeddings, ids = engine.generate_embeddings(movies)
    elapsed = time.time() - start_time
    
    logger.info(
        f"Generated {len(embeddings)} embeddings (dim={embeddings.shape[1]}) "
        f"in {elapsed:.2f} seconds ({elapsed/len(movies):.4f} sec/movie)"
    )
    return embeddings, ids

def save_embeddings_with_ids(embeddings: np.ndarray, ids: list) -> None:
    """Save embeddings and corresponding IDs as a tuple to disk."""
    logger.info(f"Saving embeddings and IDs to {EMBEDDINGS_PKL}")
    with EMBEDDINGS_PKL.open("wb") as f:
        pickle.dump((embeddings, ids), f, protocol=pickle.HIGHEST_PROTOCOL)

def build_and_save_index(embeddings: np.ndarray, ids: list) -> None:
    """Build and persist FAISS index."""
    logger.info("Building FAISS index...")
    start_time = time.time()
    
    vector_db = VectorDB.build_index(
        embeddings=embeddings,
        ids=ids,
        use_gpu=False  # Change to True if GPU available
    )
    
    # Create parent directory if needed
    FAISS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    vector_db.save_index(str(FAISS_INDEX))
    
    elapsed = time.time() - start_time
    logger.info(
        f"Built and saved index with {len(vector_db)} items "
        f"in {elapsed:.2f} seconds"
    )

def validate_outputs() -> None:
    """Verify that all outputs were created successfully."""
    if not EMBEDDINGS_PKL.exists():
        raise FileNotFoundError("Embeddings file was not created")
    if not FAISS_INDEX.exists():
        raise FileNotFoundError("FAISS index file was not created")
    logger.info("All output files validated successfully")

def main() -> None:
    """Main orchestration function."""
    try:
        total_start = time.time()
        
        # Step 1: Load movie data
        movies = load_movies()
        
        # Step 2: Generate embeddings
        embeddings, ids = generate_embeddings(movies)
        
        # Step 3: Save embeddings + ids
        save_embeddings_with_ids(embeddings, ids)
        
        # Step 4: Build and save index
        build_and_save_index(embeddings, ids)
        
        # Final validation
        validate_outputs()
        
        total_elapsed = time.time() - total_start
        logger.info(
            f"✨ Precompute completed successfully in {total_elapsed:.2f} seconds ✨"
        )
    
    except Exception as e:
        logger.error(f"Precompute failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
