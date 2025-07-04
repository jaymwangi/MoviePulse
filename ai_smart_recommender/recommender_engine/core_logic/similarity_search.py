# ai_smart_recommender/recommender_engine/core_logic/similarity_search.py
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import pickle
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

# ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / "similarity_search.log"
file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

class SimilaritySearch:
    """
    Efficient cosine similarity search for movie embeddings
    Features:
    - Batch processing for optimal performance
    - Top-k results with scores
    - Embedding normalization
    - Memory-efficient operations
    """
    
    def __init__(self, embeddings_path: Path):
        self.embeddings = self._load_embeddings(embeddings_path)
        self._preprocess_embeddings()
        
    def _load_embeddings(self, path: Path) -> Dict[int, np.ndarray]:
        """Load and validate embeddings file"""
        try:
            with open(path, 'rb') as f:
                embeddings = pickle.load(f)
                if not isinstance(embeddings, dict):
                    raise ValueError("Embeddings must be dictionary")
                logger.info(f"Loaded {len(embeddings)} embeddings from {path}")
                return embeddings
        except Exception as e:
            logger.error(f"Failed to load embeddings: {str(e)}")
            raise

    def _preprocess_embeddings(self):
        """Normalize embeddings and create search index"""
        self.movie_ids = np.array(list(self.embeddings.keys()))
        self.embedding_matrix = np.array(list(self.embeddings.values()))
        norms = np.linalg.norm(self.embedding_matrix, axis=1, keepdims=True)
        self.normalized_embeddings = self.embedding_matrix / norms
        logger.info("Preprocessed and normalized embeddings successfully")

    def find_similar(
        self,
        target_movie_id: int,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Tuple[int, float]]:
        """
        Find similar movies using cosine similarity
        """
        if target_movie_id not in self.embeddings:
            logger.warning(f"Target movie {target_movie_id} not in embeddings")
            return []

        target_idx = np.where(self.movie_ids == target_movie_id)[0][0]
        target_embedding = self.normalized_embeddings[target_idx].reshape(1, -1)
        similarities = cosine_similarity(target_embedding, self.normalized_embeddings)[0]

        similar_indices = np.argsort(similarities)[::-1]
        valid_indices = [
            i for i in similar_indices
            if i != target_idx and similarities[i] >= min_similarity
        ][:top_k]

        results = [
            (int(self.movie_ids[i]), float(similarities[i]))
            for i in valid_indices
        ]
        logger.info(f"Found {len(results)} similar movies for target {target_movie_id}")
        return results

    def batch_find_similar(
        self,
        target_movie_ids: List[int],
        top_k: int = 5
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Batch process multiple movie searches
        """
        results = {}
        for movie_id in target_movie_ids:
            results[movie_id] = self.find_similar(movie_id, top_k)
        logger.info(f"Batch similarity search completed for {len(target_movie_ids)} targets")
        return results
