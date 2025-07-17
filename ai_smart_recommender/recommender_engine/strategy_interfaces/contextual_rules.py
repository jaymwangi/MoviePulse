"""
Contextual Recommendation Strategies

Handles genre-based and mood-based recommendation strategies following the
RecommendationStrategy protocol.
"""

from dataclasses import dataclass
from typing import List, Dict, Set,Any
import json
from pathlib import Path
import logging

from core_config import constants
from service_clients import tmdb_client
from ...rec_pipeline import Recommendation, BaseRecommender
logger = logging.getLogger(__name__)

@dataclass
class GenreRecommendationStrategy(BaseRecommender):
    """
    Genre-based recommendation strategy using genre similarity scoring.
    """
    genre_mappings: Dict[str, Dict]  # movie_id -> genre data
    strategy_name: str = "genre_based"

    @classmethod
    def from_json_file(cls, file_path: Path) -> 'GenreRecommendationStrategy':
        """Factory method to load from JSON data file"""
        try:
            with open(file_path, 'r') as f:
                mappings = json.load(f)
            logger.info(f"Loaded genre mappings for {len(mappings)} movies")
            return cls(genre_mappings=mappings)
        except Exception as e:
            logger.error(f"Failed to load genre mappings: {str(e)}")
            return cls(genre_mappings={})

    def execute(self, context: dict) -> List[Recommendation]:
        """
        Generate recommendations based on genre similarity.
        
        Args:
            context: Must contain 'genre_ids' (List[int]) and 'limit' (int)
            
        Returns:
            List of Recommendation objects sorted by genre match score
        """
        if not context.get('genre_ids'):
            return []

        target_genres = self._get_target_genres(context)
        scored_movies = self._score_movies_by_genre(target_genres)
        return self._format_recommendations(
            scored_movies[:context.get('limit', 5)],
            context
        )

    def _get_target_genres(self, context: dict) -> Set[str]:
        """Extract and validate target genres from context"""
        return set(str(g_id) for g_id in context['genre_ids'])

    def _score_movies_by_genre(self, target_genres: Set[str]) -> List[tuple]:
        """Score movies based on genre overlap"""
        scored = []
        for movie_id, data in self.genre_mappings.items():
            movie_genres = set(data.get('genre_ids', []))
            overlap = movie_genres & target_genres
            if overlap:
                score = len(overlap) / len(target_genres)
                scored.append((int(movie_id), score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _format_recommendations(
        self, 
        scored_movies: List[tuple], 
        context: dict
    ) -> List[Recommendation]:
        """Convert raw scores to Recommendation objects"""
        return [
            Recommendation(
                movie_id=movie_id,
                title=self._get_movie_title(movie_id),
                reason=f"Matched {score:.0%} of your preferred genres",
                score=score,
                strategy_used=self.strategy_name,
                metadata={
                    'genres': self._get_movie_genres(movie_id),
                    'match_score': score
                }
            )
            for movie_id, score in scored_movies
        ]

    def _get_movie_title(self, movie_id: int) -> str:
        """Get movie title with caching"""
        movie = tmdb_client.get_movie_details(movie_id)
        return getattr(movie, 'title', 'Unknown')

    def _get_movie_genres(self, movie_id: int) -> List[str]:
        """Get genre names for a movie"""
        movie = tmdb_client.get_movie_details(movie_id)
        return [g.name for g in getattr(movie, 'genres', [])]
class MoodRecommendationStrategy(BaseRecommender):
    """
    Mood-based recommendation strategy using mood-to-genre mappings.
    """
    def __init__(
        self,
        mood_genre_map: Dict[str, Dict[str, Any]],
        genre_mappings: Dict[int, str],
        logger: logging.Logger = logger
    ):
        self.mood_genre_map = mood_genre_map or self._default_mood_map()
        self.genre_mappings = genre_mappings
        self.logger = logger

    @property
    def strategy_name(self) -> str:
        return "mood_based"

    @staticmethod
    def _default_mood_map() -> Dict[str, Dict[str, Any]]:
        """Fallback mood-to-genre map in case of missing data."""
        return {
            "uplifting": {
                "genres": [35, 10751, 10402],
                "weight": 1.2,
                "description": "Feel-good and inspiring"
            },
            "melancholic": {
                "genres": [18, 36, 10749],
                "weight": 1.0,
                "description": "Bittersweet and emotional"
            }
            # Add more if needed
        }

    def execute(self, context: dict) -> List[Recommendation]:
        """
        Generate recommendations based on a user's mood.
        
        Args:
            context: {
                'mood': str,
                'limit': int
            }

        Returns:
            List of Recommendation objects
        """
        mood = context.get('mood', '').lower()
        limit = context.get('limit', 5)

        if not mood or mood not in self.mood_genre_map:
            self.logger.warning(f"Unknown or missing mood: '{mood}'")
            return []

        mood_entry = self.mood_genre_map[mood]
        genre_ids = mood_entry["genres"]
        weight = mood_entry.get("weight", 1.0)

        genre_context = {
            'genre_ids': genre_ids,
            'limit': limit,
            'mood': mood
        }

        genre_strategy = GenreRecommendationStrategy(self.genre_mappings, self.logger)
        recs = genre_strategy.execute(genre_context)

        for rec in recs:
            rec.score *= weight  # 🎯 adjust score if using weighting
            rec.reason = f"Great for '{mood}' moods"
            rec.metadata["mood"] = mood
            rec.metadata["mood_weight"] = weight

        return recs
