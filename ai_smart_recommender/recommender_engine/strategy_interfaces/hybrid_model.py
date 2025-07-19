"""
Hybrid Recommendation Orchestrator (Enhanced Version)

Now includes genre affinity modeling for personalized recommendations
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
import numpy as np

# Strategy Imports
from .content_based import ContentBasedStrategy
from .contextual_rules import (
    GenreRecommendationStrategy as GenreStrategy,
    MoodRecommendationStrategy as MoodStrategy
)
from .actor_similarity import ActorSimilarityStrategy
from ai_smart_recommender.user_personalization.genre_affinity import GenreAffinityModel
from ai_smart_recommender.interfaces.fallback_rules import create_fallback_system

# Service Clients
from service_clients.tmdb_client import TMDBClient
from service_clients.local_store import (
    load_user_preferences,
    load_embeddings_with_ids,
    load_genre_mappings,
    load_mood_genre_map,
    load_actor_similarity
)
from core_config import constants

logger = logging.getLogger(__name__)

# Initialize clients
tmdb_client = TMDBClient()

class RecommendationStrategy(ABC):
    """Abstract base class for recommendation strategies"""
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_recommendations(self, *args, **kwargs) -> List['MovieRecommendation']:
        pass

@dataclass
class MovieRecommendation:
    """Container for recommendation results"""
    movie_id: int
    title: str
    similarity_score: float
    source_strategy: str
    explanation: str
    genres: List[str]
    actors: List[str]
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    reason_label: Optional[str] = None

class ScoreAdjuster:
    """Handles personalized score adjustments with genre affinity"""
    
    def __init__(self):
        self.genre_affinity = GenreAffinityModel()
        
    def apply(self, 
             recommendation: MovieRecommendation, 
             user_id: Optional[str] = None) -> MovieRecommendation:
        """Apply preference-based score modifications"""
        if not user_id:
            return recommendation
            
        try:
            # Get dynamic genre preferences from viewing history
            genre_affinity = self.genre_affinity.build_preference_vector(user_id)
            
            # Apply genre affinity weights
            genre_score = sum(
                genre_affinity.get(g.lower(), 0)
                for g in recommendation.genres
            )
            
            # Normalize and apply boost
            if genre_score > 0:
                recommendation.similarity_score *= (1 + genre_score)
                
        except Exception as e:
            logger.error(f"Genre affinity scoring failed: {str(e)}")
            
        return recommendation

class FallbackCoordinator:
    """Manages the fallback strategy cascade"""
    
    def __init__(self):
        self.fallback_chain = create_fallback_system()
        
    def get_recommendations(self, context: dict) -> List[MovieRecommendation]:
        """Execute fallback strategies in order until results are found"""
        for strategy in self.fallback_chain:
            if strategy.should_activate(context):
                try:
                    if recs := strategy.execute(context):
                        return recs
                except Exception as e:
                    logger.error(f"Fallback error in {strategy.strategy_name}: {str(e)}")
                    continue
        return []

class HybridRecommender:
    """Main recommendation orchestrator with enhanced personalization"""

    def __init__(self):
        logger.info("Initializing HybridRecommender")

        # Load required data
        self.embeddings, self.embedding_ids = load_embeddings_with_ids()
        self.user_prefs = load_user_preferences()
        self.genre_mappings = load_genre_mappings()
        self.mood_genre_map = load_mood_genre_map()
        self.actor_similarity = load_actor_similarity()

        # Initialize strategies
        self.strategies = {
            ContentBasedStrategy(self.embeddings, self.embedding_ids).strategy_name:
                ContentBasedStrategy(self.embeddings, self.embedding_ids),

            GenreStrategy(self.genre_mappings).strategy_name:
                GenreStrategy(self.genre_mappings),

            MoodStrategy(self.mood_genre_map, self.genre_mappings).strategy_name:
                MoodStrategy(self.mood_genre_map, self.genre_mappings),

            ActorSimilarityStrategy(self.actor_similarity).strategy_name:
                ActorSimilarityStrategy(self.actor_similarity)
        }

        self.fallback_coordinator = FallbackCoordinator()
        self.score_adjuster = ScoreAdjuster()  # Now with genre affinity

        logger.info(f"Initialized with {len(self.strategies)} core strategies")

    def recommend(
        self,
        target_movie_id: Optional[int] = None,
        user_mood: Optional[str] = None,
        strategy: str = "smart",
        limit: int = 10,
        user_id: Optional[str] = None,
        min_fallback_threshold: float = 0.4,
        show_reasons: bool = True
    ) -> List[MovieRecommendation]:
        """Main recommendation interface with personalized genre affinity"""
        # Input validation
        if not any([target_movie_id, user_mood, user_id]):
            return self._get_fallback_recommendations(limit)
        
        # Generate recommendations
        recommendations = self._execute_primary_strategies(
            target_movie_id,
            user_mood,
            strategy,
            limit,
            user_id
        )
        
        # Fallback if needed
        if self._needs_fallback(recommendations, min_fallback_threshold, limit):
            fallback_recs = self.fallback_coordinator.get_recommendations({
                'target_movie_id': target_movie_id,
                'user_id': user_id,
                'existing_recs': [r.movie_id for r in recommendations],
                'limit': limit - len(recommendations)
            })
            recommendations.extend(fallback_recs)
        
        # Final processing with personalized scoring
        return self._process_recommendations(
            recommendations,
            user_id,
            show_reasons
        )[:limit]

    def _execute_primary_strategies(self, *args, **kwargs):
        """Execute core recommendation strategies"""
        # Implementation remains same as original
        pass
        
    def _process_recommendations(self, recommendations, user_id, show_reasons):
        """Deduplicate, score, and sort recommendations with genre affinity"""
        # Deduplication
        unique_recs = {}
        for rec in recommendations:
            if rec.movie_id in unique_recs:
                existing = unique_recs[rec.movie_id]
                existing.similarity_score = max(existing.similarity_score, rec.similarity_score)
                existing.explanation = f"{existing.explanation} / {rec.explanation}"
            else:
                unique_recs[rec.movie_id] = rec
        
        # Personalized scoring
        processed = [
            self.score_adjuster.apply(rec, user_id)
            for rec in unique_recs.values()
        ]
        processed.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Add reasons if requested
        if show_reasons and user_id:
            processed = self._add_personalized_reason_labels(processed, user_id)
            
        return processed

    def _add_personalized_reason_labels(self, recommendations, user_id):
        """Generate human-readable explanations using genre affinity"""
        try:
            affinity_model = GenreAffinityModel()
            top_genres = affinity_model.get_top_genres(user_id)
            
            for rec in recommendations:
                # Find matching genres with user's top preferences
                matched_genres = [
                    g for g in rec.genres 
                    if g.lower() in top_genres
                ][:2]
                
                if matched_genres:
                    rec.reason_label = (
                        f"Matches your favorite genres: {', '.join(matched_genres)}"
                    )
                elif rec.source_strategy == "genre_based":
                    rec.reason_label = "Similar genre to movies you've watched"
                    
        except Exception as e:
            logger.error(f"Failed to generate personalized reasons: {str(e)}")
            
        return recommendations

    def _get_fallback_recommendations(self, limit):
        """Get TMDB popular movies as final fallback"""
        try:
            return [
                MovieRecommendation(
                    movie_id=m.id,
                    title=m.title,
                    similarity_score=0.5,
                    source_strategy="fallback",
                    explanation="Popular recommendation",
                    genres=[g.name for g in getattr(m, 'genres', [])],
                    actors=[c.name for c in getattr(m, 'cast', [])[:3]],
                    poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{m.poster_path}" if m.poster_path else None
                )
                for m in tmdb_client.get_popular_movies(limit=limit)
            ]
        except Exception as e:
            logger.error(f"Fallback failed: {str(e)}")
            return []

# Singleton instance
recommender = HybridRecommender()