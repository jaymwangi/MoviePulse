"""
Hybrid Recommendation Orchestrator (Final Version)

Combines content-based, collaborative, and contextual filtering with:
- Intelligent fallback mechanisms
- Personalized score adjustments
- Multi-strategy blending
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
    """Handles personalized score adjustments"""
    
    @staticmethod
    def apply(recommendation: MovieRecommendation, 
             user_prefs: Dict) -> MovieRecommendation:
        """Apply preference-based score modifications"""
        if not user_prefs:
            return recommendation
            
        # Get preferences
        preferred_genres = set(user_prefs.get("preferred_genres", []))
        disliked_genres = set(user_prefs.get("disliked_genres", []))
        preferred_actors = set(user_prefs.get("preferred_actors", []))
        preferred_moods = [m.lower() for m in user_prefs.get("preferred_moods", [])]
        
        # Apply adjustments
        if any(g in disliked_genres for g in recommendation.genres):
            recommendation.similarity_score *= 0.5  # Strong penalty
            
        if any(g in preferred_genres for g in recommendation.genres):
            recommendation.similarity_score *= 1.15  # Genre boost
            
        if any(a in preferred_actors for a in recommendation.actors):
            recommendation.similarity_score *= 1.25  # Actor boost
            
        if any(m in recommendation.explanation.lower() for m in preferred_moods):
            recommendation.similarity_score *= 1.3  # Mood boost
            
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
    """Main recommendation orchestrator"""

    def __init__(self):
        logger.info("Initializing HybridRecommender")

        # Load required data
        self.embeddings, self.embedding_ids = load_embeddings_with_ids()
        self.user_prefs = load_user_preferences()
        self.genre_mappings = load_genre_mappings()
        self.mood_genre_map = load_mood_genre_map()  # ✅ Required for MoodStrategy
        self.actor_similarity = load_actor_similarity()  # ✅ Load actor similarity data

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
        """Main recommendation interface"""
        # Input validation
        if not any([target_movie_id, user_mood, user_id]):
            return self._get_fallback_recommendations(limit)
        
        # Get context
        user_prefs = self._get_user_preferences(user_id)
        
        # Generate recommendations
        recommendations = self._execute_primary_strategies(
            target_movie_id,
            user_mood,
            strategy,
            limit,
            user_prefs
        )
        
        # Fallback if needed
        if self._needs_fallback(recommendations, min_fallback_threshold, limit):
            fallback_recs = self.fallback_coordinator.get_recommendations({
                'target_movie_id': target_movie_id,
                'user_prefs': user_prefs,
                'existing_recs': [r.movie_id for r in recommendations],
                'limit': limit - len(recommendations)
            })
            recommendations.extend(fallback_recs)
        
        # Final processing
        return self._process_recommendations(
            recommendations,
            user_prefs,
            show_reasons
        )[:limit]

    # Helper methods
    def _execute_primary_strategies(self, *args, **kwargs):
        """Execute core recommendation strategies"""
        # Implementation remains same as original
        pass
        
    def _process_recommendations(self, recommendations, user_prefs, show_reasons):
        """Deduplicate, score, and sort recommendations"""
        # Deduplication
        unique_recs = {}
        for rec in recommendations:
            if rec.movie_id in unique_recs:
                existing = unique_recs[rec.movie_id]
                existing.similarity_score = max(existing.similarity_score, rec.similarity_score)
                existing.explanation = f"{existing.explanation} / {rec.explanation}"
            else:
                unique_recs[rec.movie_id] = rec
        
        # Scoring and sorting
        processed = [
            ScoreAdjuster.apply(rec, user_prefs)
            for rec in unique_recs.values()
        ]
        processed.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Add reasons if requested
        if show_reasons:
            processed = self._add_reason_labels(processed, user_prefs)
            
        return processed

    def _add_reason_labels(self, recommendations, user_prefs):
        """Generate human-readable explanation strings"""
        reason_map = {
            "content_based": "Similar to content you've enjoyed",
            "genre_based": "Matches your favorite genres",
            "mood_based": "Fits your current mood",
            "actor_based": "Features actors you like",
            "hybrid": "Combines multiple factors you enjoy"
        }
        
        for rec in recommendations:
            if rec.source_strategy in reason_map:
                rec.reason_label = reason_map[rec.source_strategy]
                # Add specific details if available
                if rec.source_strategy == "genre_based" and user_prefs.get("preferred_genres"):
                    matched = [g for g in rec.genres if g in user_prefs["preferred_genres"]]
                    if matched:
                        rec.reason_label = f"Matches your favorite genres: {', '.join(matched[:2])}"
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