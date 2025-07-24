"""
Hybrid Recommendation Orchestrator (Enhanced Version)

Now includes:
- Genre affinity modeling
- Date Night Mode support
- Enhanced fallback system
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
    date_night_boost: Optional[float] = None  # New field for date night scoring

class ScoreAdjuster:
    """Handles personalized score adjustments with genre affinity"""
    
    def __init__(self):
        self.genre_affinity = GenreAffinityModel()
        
    def apply(self, 
             recommendation: MovieRecommendation, 
             user_id: Optional[str] = None,
             is_date_night: bool = False) -> MovieRecommendation:
        """Apply preference-based score modifications"""
        if not user_id and not is_date_night:
            return recommendation
            
        try:
            if is_date_night:
                # Special scoring for date night mode
                recommendation.date_night_boost = self._calculate_date_night_boost(
                    recommendation
                )
                recommendation.similarity_score *= (1 + recommendation.date_night_boost)
            else:
                # Normal personalization
                genre_affinity = self.genre_affinity.build_preference_vector(user_id)
                genre_score = sum(
                    genre_affinity.get(g.lower(), 0)
                    for g in recommendation.genres
                )
                if genre_score > 0:
                    recommendation.similarity_score *= (1 + genre_score)
                
        except Exception as e:
            logger.error(f"Scoring adjustment failed: {str(e)}")
            
        return recommendation

    def _calculate_date_night_boost(self, recommendation: MovieRecommendation) -> float:
        """Special boost calculation for date night recommendations"""
        # Base boost for genre diversity
        unique_genres = len(set(recommendation.genres))
        genre_boost = min(0.2, unique_genres * 0.05)
        
        # Additional boost for romance/drama in date night
        romance_boost = 0.15 if any(g.lower() in ['romance', 'drama'] 
                             for g in recommendation.genres) else 0
        
        return min(0.3, genre_boost + romance_boost)  # Cap total boost at 30%

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
        self.score_adjuster = ScoreAdjuster()

        logger.info(f"Initialized with {len(self.strategies)} core strategies")

    def recommend(
        self,
        target_movie_id: Optional[int] = None,
        user_mood: Optional[str] = None,
        strategy: str = "smart",
        limit: int = 10,
        user_id: Optional[str] = None,
        min_fallback_threshold: float = 0.4,
        show_reasons: bool = True,
        is_date_night: bool = False
    ) -> List[MovieRecommendation]:
        """Main recommendation interface"""
        if is_date_night:
            return self._handle_date_night_mode(user_id, limit, show_reasons)
            
        if not any([target_movie_id, user_mood, user_id]):
            return self._get_fallback_recommendations(limit)
        
        recommendations = self._execute_primary_strategies(
            target_movie_id,
            user_mood,
            strategy,
            limit,
            user_id
        )
        
        if self._needs_fallback(recommendations, min_fallback_threshold, limit):
            fallback_recs = self.fallback_coordinator.get_recommendations({
                'target_movie_id': target_movie_id,
                'user_id': user_id,
                'existing_recs': [r.movie_id for r in recommendations],
                'limit': limit - len(recommendations)
            })
            recommendations.extend(fallback_recs)
        
        return self._process_recommendations(
            recommendations,
            user_id,
            show_reasons,
            is_date_night
        )[:limit]

    def get_from_blended_prefs(
        self,
        blended_prefs: Dict[str, any],
        limit: int = 10,
        show_reasons: bool = True
    ) -> List[MovieRecommendation]:
        """
        Generate recommendations from blended date night preferences.
        
        Args:
            blended_prefs: Dictionary containing:
                - 'genres': List of blended genres
                - 'moods': Dictionary of blended mood scores
                - 'pack_names': Tuple of source pack names
            limit: Maximum number of recommendations
            show_reasons: Whether to generate explanation labels
            
        Returns:
            List of MovieRecommendation objects
        """
        logger.info(f"Generating from blended prefs: {blended_prefs}")
        
        context = {
            'target_genres': blended_prefs.get('genres', []),
            'user_mood': self._get_primary_mood(blended_prefs.get('moods', {})),
            'mood_scores': blended_prefs.get('moods', {}),
            'source_packs': blended_prefs.get('pack_names', ("Pack A", "Pack B"))
        }
        
        recommendations = []
        
        # Mood-based with weighted scores
        if context['user_mood']:
            mood_recs = self.strategies['mood_based'].get_recommendations(
                user_mood=context['user_mood'],
                mood_weights=context['mood_scores'],
                limit=limit * 2
            )
            recommendations.extend(mood_recs)
        
        # Genre-based from blended genres
        if context['target_genres']:
            genre_recs = self.strategies['genre_based'].get_recommendations(
                target_genres=context['target_genres'],
                limit=limit * 2
            )
            recommendations.extend(genre_recs)
        
        processed = self._process_recommendations(
            recommendations,
            user_id=None,
            show_reasons=show_reasons,
            is_date_night=True
        )[:limit]
        
        if show_reasons:
            pack_a, pack_b = context['source_packs']
            for rec in processed:
                rec.explanation = (
                    f"Blended from {pack_a} & {pack_b}: {rec.explanation}"
                )
                if rec.date_night_boost:
                    rec.reason_label = (
                        f"Great match for date night (+{int(rec.date_night_boost*100)}% boost)"
                    )
        
        return processed

    def _handle_date_night_mode(
        self,
        user_id: Optional[str],
        limit: int,
        show_reasons: bool
    ) -> List[MovieRecommendation]:
        """Special handler for date night session"""
        try:
            from session_utils.state_tracker import get_blended_prefs
            blended_prefs = get_blended_prefs()
            if not blended_prefs:
                logger.warning("Date night active but no blended prefs found")
                return self._get_fallback_recommendations(limit)
                
            return self.get_from_blended_prefs(
                blended_prefs,
                limit,
                show_reasons
            )
        except Exception as e:
            logger.error(f"Date night mode failed: {str(e)}")
            return self._get_fallback_recommendations(limit)

    def _get_primary_mood(self, mood_scores: Dict[str, float]) -> Optional[str]:
        """Determine primary mood from blended scores"""
        if not mood_scores:
            return None
        
        max_mood = max(mood_scores.items(), key=lambda x: x[1])
        return max_mood[0] if max_mood[1] > 0.3 else None

    def _execute_primary_strategies(self, *args, **kwargs):
        """Execute core recommendation strategies"""
        # Implementation remains same as original
        pass
        
    def _process_recommendations(
        self,
        recommendations: List[MovieRecommendation],
        user_id: Optional[str],
        show_reasons: bool,
        is_date_night: bool = False
    ) -> List[MovieRecommendation]:
        """Process recommendations with optional personalization"""
        unique_recs = {}
        for rec in recommendations:
            if rec.movie_id in unique_recs:
                existing = unique_recs[rec.movie_id]
                existing.similarity_score = max(existing.similarity_score, rec.similarity_score)
                existing.explanation = f"{existing.explanation} / {rec.explanation}"
            else:
                unique_recs[rec.movie_id] = rec
        
        processed = [
            self.score_adjuster.apply(rec, user_id, is_date_night)
            for rec in unique_recs.values()
        ]
        processed.sort(key=lambda x: x.similarity_score, reverse=True)
        
        if show_reasons and (user_id or is_date_night):
            processed = self._add_reason_labels(processed, user_id, is_date_night)
            
        return processed

    def _add_reason_labels(
        self,
        recommendations: List[MovieRecommendation],
        user_id: Optional[str],
        is_date_night: bool
    ) -> List[MovieRecommendation]:
        """Generate appropriate reason labels"""
        try:
            if is_date_night:
                return recommendations  # Already handled in get_from_blended_prefs
                
            affinity_model = GenreAffinityModel()
            top_genres = affinity_model.get_top_genres(user_id)
            
            for rec in recommendations:
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
            logger.error(f"Failed to generate reasons: {str(e)}")
            
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