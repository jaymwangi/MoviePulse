"""
Content-Based Recommendation Strategy

Implements content-based filtering using movie embeddings and cosine similarity.
"""

from dataclasses import dataclass
from typing import List, Dict,Optional
import numpy as np
import pickle
import logging
from sklearn.metrics.pairwise import cosine_similarity

from core_config import constants
from service_clients import tmdb_client
from ...interfaces.base_recommender import Recommendation, BaseRecommender


logger = logging.getLogger(__name__)

@dataclass
class ContentBasedStrategy(BaseRecommender):
    """
    Content-based recommendation strategy using movie embeddings.
    
    Attributes:
        embeddings: Dictionary mapping movie IDs to their embeddings
        min_similarity: Minimum similarity threshold for recommendations
    """
    embeddings: Dict[int, np.ndarray]
    min_similarity: float = 0.3

    @classmethod
    def create(cls) -> 'ContentBasedStrategy':
        """
        Factory method to create strategy with loaded embeddings.
        
        Returns:
            ContentBasedStrategy instance with loaded embeddings
            
        Raises:
            RuntimeError: If embeddings fail to load
        """
        try:
            with open(constants.EMBEDDINGS_FILE, 'rb') as f:
                embeddings = pickle.load(f)
            logger.info(f"Loaded embeddings for {len(embeddings)} movies")
            return cls(embeddings=embeddings)
        except Exception as e:
            logger.error(f"Failed to load embeddings: {str(e)}")
            raise RuntimeError("Could not initialize content-based strategy") from e

    @property
    def strategy_name(self) -> str:
        """Unique identifier for this strategy"""
        return "content_based"

    def execute(self, context: Dict) -> List[Recommendation]:
        """
        Generate content-based recommendations.
        
        Args:
            context: Dictionary containing:
                - target_movie_id: ID of movie to find similar items for
                - limit: Maximum number of recommendations to return
                - min_similarity: Optional override for similarity threshold
                
        Returns:
            List of Recommendation objects sorted by similarity score
        """
        target_id = context.get('target_movie_id')
        if not target_id or target_id not in self.embeddings:
            logger.debug("No valid target movie ID provided")
            return []

        limit = context.get('limit', 5)
        min_sim = context.get('min_similarity', self.min_similarity)

        try:
            target_embedding = self.embeddings[target_id].reshape(1, -1)
            all_ids = np.array(list(self.embeddings.keys()))
            all_embeddings = np.array(list(self.embeddings.values()))
            
            sim_scores = cosine_similarity(target_embedding, all_embeddings)[0]
            
            # Get top matches excluding self
            top_indices = np.argsort(sim_scores)[-limit-1:-1][::-1]
            valid_indices = [i for i in top_indices if sim_scores[i] >= min_sim]
            
            return [
                self._create_recommendation(
                    movie_id=all_ids[idx],
                    score=float(sim_scores[idx]),
                    context=context
                )
                for idx in valid_indices
            ]
        except Exception as e:
            logger.error(f"Content-based recommendation failed: {str(e)}")
            return []

    def _create_recommendation(self, movie_id: int, score: float, context: Dict) -> Recommendation:
        """
        Create a Recommendation object from movie data.
        
        Args:
            movie_id: TMDB movie ID
            score: Similarity score (0-1)
            context: Original context dictionary
            
        Returns:
            Recommendation object with populated fields
        """
        try:
            movie = tmdb_client.get_movie_details(movie_id)
            if not movie:
                raise ValueError(f"Movie {movie_id} not found")
                
            return Recommendation(
                content_id=str(movie_id),
                title=movie.title,
                reason="Similar content and themes",
                score=score,
                strategy_used=self.strategy_name,
                metadata={
                    'genres': [g.name for g in getattr(movie, 'genres', [])],
                    'actors': [c.name for c in getattr(movie, 'cast', [])[:3]],
                    'poster_url': self._get_poster_url(movie),
                    'backdrop_url': self._get_backdrop_url(movie),
                    'year': getattr(movie, 'release_date', '')[:4]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to create recommendation for movie {movie_id}: {str(e)}")
            return Recommendation(
                content_id=str(movie_id),
                title=f"Movie {movie_id}",
                reason="Content-based match",
                score=score,
                strategy_used=self.strategy_name,
                metadata={'error': str(e)}
            )

    def _get_poster_url(self, movie) -> Optional[str]:
        """Generate full poster URL if path exists"""
        if getattr(movie, 'poster_path', None):
            return f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}"
        return None

    def _get_backdrop_url(self, movie) -> Optional[str]:
        """Generate full backdrop URL if path exists"""
        if getattr(movie, 'backdrop_path', None):
            return f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}"
        return None