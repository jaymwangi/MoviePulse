# ai_smart_recommender/recommender_engine/strategy_interfaces/__init__.py

from .content_based import ContentBasedStrategy
from .contextual_rules import GenreRecommendationStrategy, MoodRecommendationStrategy
from .actor_similarity import ActorSimilarityStrategy

__all__ = [
    "ContentBasedStrategy",
    "GenreRecommendationStrategy",
    "MoodRecommendationStrategy",
    "ActorSimilarityStrategy"
]
