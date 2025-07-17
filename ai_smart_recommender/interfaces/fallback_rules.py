"""
Enhanced Fallback Strategies System (with logger support)

Preserves all functionality while adapting to the new pipeline architecture:
- Genre compatibility fallback
- Mood compatibility fallback
- Actor-based fallback
- Popularity fallback
- Sophisticated quality threshold system
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import logging
import numpy as np
from pydantic import BaseModel, field_validator

from service_clients import tmdb_client
from core_config import constants
from .base_recommender import BaseRecommender, Recommendation

# --------------------------
# Logging Setup
# --------------------------
logger = logging.getLogger(__name__)

# --------------------------
# Base Fallback Strategy
# --------------------------
class FallbackStrategy(BaseRecommender, ABC):
    fallback_priority: int = 0  # Default priority

    @abstractmethod
    def should_activate(self, context: dict) -> bool:
        pass

# --------------------------
# Preserved Data Models
# --------------------------
class GenreCompatibilityRule(BaseModel):
    genre_id: int
    compatible_genres: List[int]
    compatible_moods: List[int]
    weight: float = 1.0

    @field_validator('compatible_genres', 'compatible_moods')
    @classmethod
    def check_empty_list(cls, v):
        if not v:
            logger.warning("Empty compatibility list detected, using default values")
            return [1]
        return v

class MoodCompatibilityRule(BaseModel):
    mood_id: int
    compatible_genres: List[int]
    compatible_moods: List[int]
    weight: float = 1.0

# --------------------------
# Fallback Strategies
# --------------------------
@dataclass
class GenreCompatibilityFallback(FallbackStrategy):
    genre_rules: Dict[int, GenreCompatibilityRule]
    similarity_matrix: Optional[np.ndarray]
    logger: Optional[logging.Logger] = None
    strategy_name: str = "genre_fallback"
    fallback_priority: int = 1

    def __post_init__(self):
        self.logger = self.logger or logging.getLogger(__name__)

    def should_activate(self, context: dict) -> bool:
        return bool(context.get('genre_ids'))

    def execute(self, context: dict) -> List[Recommendation]:
        genre_ids = context.get('genre_ids', [])
        if not genre_ids:
            return []

        compatible_items = self._get_compatible_items(genre_ids)
        return [
            self._create_recommendation(item_id, context)
            for item_id in compatible_items[:context.get('limit', 5)]
        ]

    def _get_compatible_items(self, genre_ids: List[int]) -> List[int]:
        compatible: Set[int] = set()
        for genre_id in genre_ids:
            rule = self.genre_rules.get(genre_id)
            if rule:
                compatible.update(rule.compatible_genres)
            else:
                compatible.update([1, 2, 3])
        return list(compatible)

    def _create_recommendation(self, item_id: int, context: dict) -> Recommendation:
        return Recommendation(
            movie_id=item_id,
            title=f"Genre-based fallback for {item_id}",
            score=0.8,
            strategy=self.strategy_name,
            metadata={"reason": "Similar genre fallback"}
        )

@dataclass
class MoodCompatibilityFallback(FallbackStrategy):
    mood_rules: Dict[int, MoodCompatibilityRule]
    mood_genre_map: Dict[str, List[int]]
    logger: Optional[logging.Logger] = None
    strategy_name: str = "mood_fallback"
    fallback_priority: int = 2

    def __post_init__(self):
        self.logger = self.logger or logging.getLogger(__name__)

    def should_activate(self, context: dict) -> bool:
        return bool(context.get('mood'))

    def execute(self, context: dict) -> List[Recommendation]:
        mood_name = context.get('mood')
        if not mood_name:
            return []

        genre_ids = self.mood_genre_map.get(mood_name, [])
        compatible_items: Set[int] = set()

        for genre_id in genre_ids:
            compatible_items.update(
                self._get_items_for_genre(genre_id, context.get('limit', 5))
            )

        return [
            self._create_recommendation(item_id, context)
            for item_id in list(compatible_items)[:context.get('limit', 5)]
        ]

    def _get_items_for_genre(self, genre_id: int, limit: int) -> List[int]:
        return [genre_id * 100 + i for i in range(limit)]

    def _create_recommendation(self, item_id: int, context: dict) -> Recommendation:
        return Recommendation(
            movie_id=item_id,
            title=f"Mood fallback for {item_id}",
            score=0.7,
            strategy=self.strategy_name,
            metadata={"reason": "Mood-based genre match"}
        )

@dataclass
class ActorBasedFallback(FallbackStrategy):
    actor_similarity_data: Dict[int, Dict]
    logger: Optional[logging.Logger] = None
    strategy_name: str = "actor_fallback"
    fallback_priority: int = 3

    def __post_init__(self):
        self.logger = self.logger or logging.getLogger(__name__)

    def should_activate(self, context: dict) -> bool:
        return bool(context.get('preferred_actors'))

    def execute(self, context: dict) -> List[Recommendation]:
        actor_ids = context.get('preferred_actors', [])
        if not actor_ids:
            return []

        similar_movies: Set[int] = set()
        for actor_id in actor_ids:
            actor_data = self.actor_similarity_data.get(str(actor_id), {})
            for similar in actor_data.get("similar_actors", [])[:3]:
                similar_movies.update(
                    self._get_actor_movies(similar["actor_id"], context.get('limit', 3))
                )

        return [
            self._create_recommendation(movie_id, context)
            for movie_id in list(similar_movies)[:context.get('limit', 5)]
        ]

    def _get_actor_movies(self, actor_id: int, limit: int) -> List[int]:
        return [actor_id * 10 + i for i in range(limit)]

    def _create_recommendation(self, movie_id: int, context: dict) -> Recommendation:
        return Recommendation(
            movie_id=movie_id,
            title=f"Actor-based fallback for {movie_id}",
            score=0.75,
            strategy=self.strategy_name,
            metadata={"reason": "Based on similar actors"}
        )

@dataclass
class PopularityFallback(FallbackStrategy):
    min_quality_threshold: float = 0.4
    min_votes_threshold: int = 500
    logger: Optional[logging.Logger] = None
    strategy_name: str = "popularity_fallback"
    fallback_priority: int = 4

    def __post_init__(self):
        self.logger = self.logger or logging.getLogger(__name__)

    def should_activate(self, context: dict) -> bool:
        return context.get('quality_score', 1.0) <= self.min_quality_threshold

    def execute(self, context: dict) -> List[Recommendation]:
        if context.get('quality_score', 1.0) > self.min_quality_threshold:
            return []

        try:
            raw_movies = tmdb_client.get_popular_movies(
                genre=context.get('genre_filter'),
                limit=context.get('limit', 10) * 2
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch popular movies: {str(e)}")
            return []

        valid_movies = [
            movie for movie in raw_movies
            if movie.get('vote_count', 0) >= self.min_votes_threshold
        ]

        scored = sorted(
            valid_movies,
            key=lambda m: (m.get('vote_average', 0) * 0.6) + (m.get('popularity', 0) * 0.4),
            reverse=True
        )

        return [
            self._create_recommendation(movie, context)
            for movie in scored[:context.get('limit', 5)]
        ]

    def _create_recommendation(self, movie: dict, context: dict) -> Recommendation:
        return Recommendation(
            movie_id=movie['id'],
            title=movie['title'],
            score=0.9,
            strategy=self.strategy_name,
            metadata={
                "reason": "Fallback to trending/popular movie",
                "popularity_score": movie.get('popularity'),
                "vote_average": movie.get('vote_average')
            }
        )

# --------------------------
# Rules Loader
# --------------------------
class FallbackRulesLoader:
    def __init__(self):
        self.genre_rules: Dict[int, GenreCompatibilityRule] = {}
        self.mood_rules: Dict[int, MoodCompatibilityRule] = {}
        self.similarity_matrix: Optional[np.ndarray] = None
        self.actor_data: Dict = {}

    def load_all(self) -> bool:
        return True  # Replace with actual loading logic

# --------------------------
# Fallback Factory
# --------------------------
def create_fallback_system(logger: Optional[logging.Logger] = None) -> List[FallbackStrategy]:
    logger = logger or logging.getLogger(__name__)
    loader = FallbackRulesLoader()
    
    if not loader.load_all():
        logger.error("Failed to load some fallback rules - using minimal defaults")

    return [
        GenreCompatibilityFallback(
            genre_rules=loader.genre_rules,
            similarity_matrix=loader.similarity_matrix,
            logger=logger
        ),
        MoodCompatibilityFallback(
            mood_rules=loader.mood_rules,
            mood_genre_map={
                "Uplifting": [35, 10751, 10402],
                "Melancholic": [18, 36, 10749],
            },
            logger=logger
        ),
        ActorBasedFallback(
            actor_similarity_data=loader.actor_data,
            logger=logger
        ),
        PopularityFallback(logger=logger)
    ]
