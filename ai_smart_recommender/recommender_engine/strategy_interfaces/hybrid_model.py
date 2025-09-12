"""
Hybrid Recommendation Orchestrator (Enhanced Version)

Now includes:
- Genre affinity modeling
- Date Night Mode support
- Enhanced fallback system
- Critic Mode support with adjustable strategy weights
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union
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
    date_night_boost: Optional[float] = None
    critic_mode_adjustment: Optional[float] = None  # New field for critic mode adjustments

class ScoreAdjuster:
    """Handles personalized score adjustments with genre affinity and critic mode"""
    
    def __init__(self):
        self.genre_affinity = GenreAffinityModel()
        
    def apply(self, 
             recommendation: MovieRecommendation, 
             user_id: Optional[str] = None,
             is_date_night: bool = False,
             critic_mode: str = "balanced") -> MovieRecommendation:
        """Apply preference-based score modifications"""
        if not user_id and not is_date_night and critic_mode == "balanced":
            return recommendation
            
        try:
            # Apply critic mode adjustments first
            critic_adjustment = self._calculate_critic_adjustment(recommendation, critic_mode)
            recommendation.critic_mode_adjustment = critic_adjustment
            recommendation.similarity_score *= (1 + critic_adjustment)
            
            if is_date_night:
                # Special scoring for date night mode
                recommendation.date_night_boost = self._calculate_date_night_boost(
                    recommendation
                )
                recommendation.similarity_score *= (1 + recommendation.date_night_boost)
            elif user_id:
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

    def _calculate_critic_adjustment(self, recommendation: MovieRecommendation, critic_mode: str) -> float:
        """Calculate adjustment based on critic mode and movie characteristics"""
        if critic_mode == "balanced":
            return 0.0
            
        # Get movie metadata for critic mode analysis
        movie_metadata = self._get_movie_metadata(recommendation.movie_id)
        
        adjustments = {
            "arthouse": self._arthouse_adjustment(movie_metadata),
            "blockbuster": self._blockbuster_adjustment(movie_metadata),
            "indie": self._indie_adjustment(movie_metadata)
        }
        
        return adjustments.get(critic_mode, 0.0)

    def _arthouse_adjustment(self, metadata: Dict) -> float:
        """Boost for arthouse characteristics"""
        boost = 0.0
        
        # Higher boost for foreign films, documentaries, independent productions
        if metadata.get('original_language') != 'en':
            boost += 0.15
        if 'documentary' in [g.lower() for g in metadata.get('genres', [])]:
            boost += 0.10
        if metadata.get('budget', 0) < 10000000:  # Low budget
            boost += 0.08
            
        return min(0.25, boost)  # Cap at 25%

    def _blockbuster_adjustment(self, metadata: Dict) -> float:
        """Boost for blockbuster characteristics"""
        boost = 0.0
        
        # Higher boost for high-budget, action, sci-fi, franchise films
        if metadata.get('budget', 0) > 50000000:
            boost += 0.15
        if any(g in ['action', 'adventure', 'sci-fi', 'fantasy'] 
               for g in [g.lower() for g in metadata.get('genres', [])]):
            boost += 0.10
        if metadata.get('belongs_to_collection'):
            boost += 0.08
            
        return min(0.25, boost)

    def _indie_adjustment(self, metadata: Dict) -> float:
        """Boost for indie characteristics"""
        boost = 0.0
        
        # Boost for independent, comedy-drama, coming-of-age films
        if metadata.get('budget', 0) < 20000000:
            boost += 0.12
        if any(g in ['comedy', 'drama', 'romance'] 
               for g in [g.lower() for g in metadata.get('genres', [])]):
            boost += 0.08
        if metadata.get('vote_average', 0) > 7.0:  # Well-rated
            boost += 0.05
            
        return min(0.25, boost)

    def _get_movie_metadata(self, movie_id: int) -> Dict:
        """Get additional movie metadata for critic mode analysis"""
        try:
            movie = tmdb_client.get_movie_details(movie_id)
            return {
                'budget': movie.get('budget', 0),
                'genres': [g['name'] for g in movie.get('genres', [])],
                'original_language': movie.get('original_language', 'en'),
                'belongs_to_collection': movie.get('belongs_to_collection') is not None,
                'vote_average': movie.get('vote_average', 0)
            }
        except Exception:
            return {}

    def _calculate_date_night_boost(self, recommendation: MovieRecommendation) -> float:
        """Special boost calculation for date night recommendations"""
        # Base boost for genre diversity
        unique_genres = len(set(recommendation.genres))
        genre_boost = min(0.2, unique_genres * 0.05)
        
        # Additional boost for romance/drama in date night
        romance_boost = 0.15 if any(g.lower() in ['romance', 'drama'] 
                             for g in recommendation.genres) else 0
        
        return min(0.3, genre_boost + romance_boost)

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
    """Main recommendation orchestrator with enhanced personalization and critic mode"""

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
        self.critic_mode = "balanced"  # Default critic mode
        self.critic_weights = self._get_critic_weights()

        logger.info(f"Initialized with {len(self.strategies)} core strategies")

    def set_critic_mode(self, mode: str):
        """Set critic mode for recommendations"""
        valid_modes = ["balanced", "arthouse", "blockbuster", "indie"]
        if mode in valid_modes:
            self.critic_mode = mode
            self.critic_weights = self._get_critic_weights()
            logger.info(f"Critic mode set to: {mode}")
        else:
            logger.warning(f"Invalid critic mode: {mode}. Using 'balanced'.")
            self.critic_mode = "balanced"

    def _get_critic_weights(self) -> Dict[str, float]:
        """Get strategy weights based on critic mode"""
        return {
            "balanced": {"content_based": 0.4, "genre_based": 0.3, "mood_based": 0.2, "actor_based": 0.1},
            "arthouse": {"content_based": 0.6, "genre_based": 0.2, "mood_based": 0.1, "actor_based": 0.1},
            "blockbuster": {"content_based": 0.2, "genre_based": 0.4, "mood_based": 0.2, "actor_based": 0.2},
            "indie": {"content_based": 0.3, "genre_based": 0.3, "mood_based": 0.3, "actor_based": 0.1}
        }.get(self.critic_mode, {"content_based": 0.4, "genre_based": 0.3, "mood_based": 0.2, "actor_based": 0.1})

    def recommend(
        self,
        target_movie_id: Optional[int] = None,
        user_mood: Optional[str] = None,
        strategy: str = "smart",
        limit: int = 10,
        user_id: Optional[str] = None,
        min_fallback_threshold: float = 0.4,
        show_reasons: bool = True,
        is_date_night: bool = False,
        critic_mode: Optional[str] = None
    ) -> List[MovieRecommendation]:
        """Main recommendation interface with critic mode support"""
        # Set critic mode if provided
        if critic_mode:
            self.set_critic_mode(critic_mode)
            
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

    def _execute_primary_strategies(
        self,
        target_movie_id: Optional[int],
        user_mood: Optional[str],
        strategy: str,
        limit: int,
        user_id: Optional[str]
    ) -> List[MovieRecommendation]:
        """Execute core recommendation strategies with critic mode weighting"""
        all_recommendations = []
        
        # Content-based recommendations
        if target_movie_id:
            content_recs = self.strategies['content_based'].get_recommendations(
                target_movie_id=target_movie_id,
                limit=limit * 2
            )
            # Apply critic mode weight
            for rec in content_recs:
                rec.similarity_score *= self.critic_weights['content_based']
            all_recommendations.extend(content_recs)
        
        # Genre-based recommendations
        if user_id or target_movie_id:
            target_genres = self._get_target_genres(user_id, target_movie_id)
            if target_genres:
                genre_recs = self.strategies['genre_based'].get_recommendations(
                    target_genres=target_genres,
                    limit=limit * 2
                )
                # Apply critic mode weight
                for rec in genre_recs:
                    rec.similarity_score *= self.critic_weights['genre_based']
                all_recommendations.extend(genre_recs)
        
        # Mood-based recommendations
        if user_mood:
            mood_recs = self.strategies['mood_based'].get_recommendations(
                user_mood=user_mood,
                limit=limit * 2
            )
            # Apply critic mode weight
            for rec in mood_recs:
                rec.similarity_score *= self.critic_weights['mood_based']
            all_recommendations.extend(mood_recs)
        
        # Actor-based recommendations
        if target_movie_id:
            actor_recs = self.strategies['actor_based'].get_recommendations(
                target_movie_id=target_movie_id,
                limit=limit
            )
            # Apply critic mode weight
            for rec in actor_recs:
                rec.similarity_score *= self.critic_weights['actor_based']
            all_recommendations.extend(actor_recs)
        
        return all_recommendations

    def _get_target_genres(self, user_id: Optional[str], target_movie_id: Optional[int]) -> List[str]:
        """Get target genres based on user preferences or target movie"""
        if user_id:
            try:
                affinity_model = GenreAffinityModel()
                return affinity_model.get_top_genres(user_id, top_n=3)
            except Exception:
                pass
        
        if target_movie_id:
            try:
                movie_details = tmdb_client.get_movie_details(target_movie_id)
                return [genre['name'] for genre in movie_details.get('genres', [])][:3]
            except Exception:
                pass
        
        return []

    def get_from_blended_prefs(
        self,
        blended_prefs: Dict[str, any],
        limit: int = 10,
        show_reasons: bool = True
    ) -> List[MovieRecommendation]:
        """
        Generate recommendations from blended date night preferences.
        """
        logger.info(f"Generating from blended prefs: {blended_prefs}")
        
        context = {
            'target_genres': blended_prefs.get('genres', []),
            'user_mood': self._get_primary_mood(blended_prefs.get('moods', {})),
            'mood_scores': blended_prefs.get('moods', {}),
            'source_packs': blended_prefs.get('pack_names', ("Pack A", "Pack B"))
        }
        
        recommendations = []
        
        # Apply critic mode weights to blended preferences
        if context['user_mood']:
            mood_recs = self.strategies['mood_based'].get_recommendations(
                user_mood=context['user_mood'],
                mood_weights=context['mood_scores'],
                limit=limit * 2
            )
            for rec in mood_recs:
                rec.similarity_score *= self.critic_weights['mood_based']
            recommendations.extend(mood_recs)
        
        # Genre-based from blended genres
        if context['target_genres']:
            genre_recs = self.strategies['genre_based'].get_recommendations(
                target_genres=context['target_genres'],
                limit=limit * 2
            )
            for rec in genre_recs:
                rec.similarity_score *= self.critic_weights['genre_based']
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
                if rec.critic_mode_adjustment:
                    rec.reason_label += f" | Critic mode adjusted (+{int(rec.critic_mode_adjustment*100)}%)"
        
        return processed

    def _process_recommendations(
        self,
        recommendations: List[MovieRecommendation],
        user_id: Optional[str],
        show_reasons: bool,
        is_date_night: bool = False
    ) -> List[MovieRecommendation]:
        """Process recommendations with optional personalization and critic mode"""
        unique_recs = {}
        for rec in recommendations:
            if rec.movie_id in unique_recs:
                existing = unique_recs[rec.movie_id]
                existing.similarity_score = max(existing.similarity_score, rec.similarity_score)
                existing.explanation = f"{existing.explanation} / {rec.explanation}"
            else:
                unique_recs[rec.movie_id] = rec
        
        processed = [
            self.score_adjuster.apply(rec, user_id, is_date_night, self.critic_mode)
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
        """Generate appropriate reason labels with critic mode context"""
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
                
                reason_parts = []
                
                if matched_genres:
                    reason_parts.append(f"Matches your favorite genres: {', '.join(matched_genres)}")
                
                if rec.critic_mode_adjustment and rec.critic_mode_adjustment > 0:
                    mode_name = self.critic_mode.capitalize()
                    reason_parts.append(f"{mode_name} critic pick (+{int(rec.critic_mode_adjustment*100)}%)")
                
                if reason_parts:
                    rec.reason_label = " | ".join(reason_parts)
                elif rec.source_strategy == "genre_based":
                    rec.reason_label = "Similar genre to movies you've watched"
                    
        except Exception as e:
            logger.error(f"Failed to generate reasons: {str(e)}")
            
        return recommendations

    def _handle_date_night_mode(self, user_id, limit, show_reasons):
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

    def _needs_fallback(self, recommendations, threshold, limit):
        """Check if fallback recommendations are needed"""
        return len(recommendations) < limit or all(r.similarity_score < threshold for r in recommendations)

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