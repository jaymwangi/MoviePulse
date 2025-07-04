"""
Movie Embedding Engine - converts movie metadata into numerical embeddings
for use in recommendation systems.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging

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
    """
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = SentenceTransformer(model_name, device=device)
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

    def generate_embeddings(self, 
                          movies: List[Dict],
                          batch_size: int = 32) -> Tuple[np.ndarray, List[int]]:
        """
        Generate embeddings for a list of movies.
        
        Args:
            movies: List of movie dictionaries containing metadata
            batch_size: Number of texts to process at once
            
        Returns:
            Tuple containing:
                - numpy array of embeddings (shape: num_movies x embedding_dim)
                - list of corresponding movie IDs
                
        Raises:
            ValueError: If no valid movies are provided
        """
        if not movies:
            raise ValueError("No movies provided for embedding generation")
            
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
                   
        return embeddings, ids

    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings produced by this engine."""
        return self.model.get_sentence_embedding_dimension()
