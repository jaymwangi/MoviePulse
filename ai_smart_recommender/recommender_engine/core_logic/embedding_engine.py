"""
Movie Embedding Engine - converts movie metadata into numerical embeddings
for use in recommendation systems.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging
import json
import os
import pickle
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieEmbeddingEngine:
    """
    Engine for generating embeddings from movie metadata.
    
    Uses Sentence Transformers to convert text data into numerical vectors
    that capture semantic meaning for recommendation purposes.
    
    Args:
        model_name: Name of the SentenceTransformer model to use
                    (default: "all-MiniLM-L6-v2")
        device: Hardware device to use ("cpu" or "cuda")
        cache_dir: Directory to store cached embeddings (default: "static_data")
        version: Version identifier for the embeddings (default: "v2.1")
    """
    
    # Constants
    EMBEDDING_FILE = "embeddings.pkl"
    METADATA_FILE = "embedding_metadata.json"
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 device: str = "cpu",
                 cache_dir: str = "static_data",
                 version: str = "v2.1"):
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.version = version
        self.model = SentenceTransformer(model_name, device=device)
        
        # Ensure cache directory exists
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized MovieEmbeddingEngine with model: {model_name}")

    def _prepare_text(self, movie: Dict) -> str:
        """
        Prepare the text for embedding by combining relevant fields.
        
        Args:
            movie: Dictionary containing movie metadata
            
        Returns:
            Combined text string for embedding
        """
        title = movie.get('title', '')
        overview = movie.get('overview', '')
        genres = ', '.join([g.get('name', '') for g in movie.get('genres', [])])
        
        # Combine fields with appropriate weights
        return f"Title: {title}. Description: {overview}. Genres: {genres}"

    def _get_cache_paths(self) -> Tuple[Path, Path]:
        """Return paths to the embedding cache and metadata files."""
        base_path = Path(self.cache_dir)
        return (
            base_path / self.EMBEDDING_FILE,
            base_path / self.METADATA_FILE
        )

    def _load_from_cache(self) -> Optional[Tuple[np.ndarray, List[int]]]:
        """
        Attempt to load embeddings from cache if valid.
        
        Returns:
            Tuple of (embeddings, ids) if valid cache exists, else None
        """
        embedding_path, metadata_path = self._get_cache_paths()
        
        if not (embedding_path.exists() and metadata_path.exists()):
            logger.info("No cache files found")
            return None
            
        try:
            # Load metadata first
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            # Validate metadata
            if (metadata.get('model_name') != self.model_name or 
                metadata.get('version') != self.version):
                logger.info("Cache invalid due to model/version mismatch")
                return None
                
            # Load embeddings
            with open(embedding_path, 'rb') as f:
                cache_data = pickle.load(f)
                
            if (len(cache_data['ids']) != metadata['num_movies']):
                logger.warning("Cache count mismatch - regenerating")
                return None
                
            logger.info(f"Loaded {metadata['num_movies']} embeddings from cache "
                       f"(generated on {metadata['created']})")
            return cache_data['embeddings'], cache_data['ids']
            
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None

    def _save_to_cache(self, embeddings: np.ndarray, ids: List[int]) -> None:
        """
        Save generated embeddings and metadata to cache.
        
        Args:
            embeddings: Generated embeddings array
            ids: List of corresponding movie IDs
        """
        embedding_path, metadata_path = self._get_cache_paths()
        
        # Prepare metadata
        metadata = {
            'model_name': self.model_name,
            'version': self.version,
            'created': datetime.now().isoformat(),
            'num_movies': len(ids),
            'embedding_dim': embeddings.shape[1]
        }
        
        # Prepare cache data
        cache_data = {
            'embeddings': embeddings,
            'ids': ids
        }
        
        try:
            # Save embeddings
            with open(embedding_path, 'wb') as f:
                pickle.dump(cache_data, f)
                
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Saved {len(ids)} embeddings to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def generate_embeddings(self, 
                          movies: List[Dict],
                          batch_size: int = 32,
                          use_cache: bool = True) -> Tuple[np.ndarray, List[int]]:
        """
        Generate embeddings for a list of movies.
        
        Args:
            movies: List of movie dictionaries containing metadata
            batch_size: Number of texts to process at once
            use_cache: Whether to attempt loading from cache first
            
        Returns:
            Tuple containing:
                - numpy array of embeddings (shape: num_movies x embedding_dim)
                - list of corresponding movie IDs
                
        Raises:
            ValueError: If no valid movies are provided
        """
        if not movies:
            raise ValueError("No movies provided for embedding generation")
            
        # Try to load from cache first
        if use_cache:
            cached = self._load_from_cache()
            if cached is not None:
                return cached
                
        texts = []
        ids = []
        
        # Prepare texts and collect IDs
        for movie in movies:
            try:
                movie_id = movie.get('id')
                if not movie_id:
                    logger.warning(f"Movie missing ID: {movie.get('title')}")
                    continue
                    
                texts.append(self._prepare_text(movie))
                ids.append(movie_id)
            except Exception as e:
                logger.error(f"Error processing movie {movie.get('id')}: {e}")
                continue
                
        if not texts:
            raise ValueError("No valid movies could be processed")
            
        logger.info(f"Generating embeddings for {len(texts)} movies...")
        
        # Generate embeddings with progress bar
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        logger.info(f"Successfully generated {embeddings.shape[0]} embeddings "
                   f"(dimension: {embeddings.shape[1]})")
                   
        # Save to cache
        self._save_to_cache(embeddings, ids)
                   
        return embeddings, ids

    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings produced by this engine."""
        return self.model.get_sentence_embedding_dimension()