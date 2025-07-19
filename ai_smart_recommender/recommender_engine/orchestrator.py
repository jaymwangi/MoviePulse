"""
Enhanced Recommendation Pipeline Orchestrator with Personalization Integration

Key Features:
1. Personalized recommendations using watch history and genre affinity
2. Dynamic strategy weighting based on user preference vectors
3. Comprehensive recommendation metadata with affinity insights
4. Robust fallback system with cached personalization
5. Performance optimizations with lazy loading and memoization
"""

import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
from functools import lru_cache, wraps
import time
from dataclasses import asdict
from collections import defaultdict
from datetime import datetime

# Shared modules
from core_config import constants
from service_clients import tmdb_client

# Interfaces
from ..interfaces.base_recommender import Recommendation
from ..rec_pipeline import RecommendationPipeline
from ..user_personalization.watch_history import WatchHistory
from ..user_personalization.genre_affinity import GenreAffinityModel

# Strategy classes
from .strategy_interfaces.content_based import ContentBasedStrategy
from .strategy_interfaces.contextual_rules import GenreRecommendationStrategy, MoodRecommendationStrategy
from .strategy_interfaces.actor_similarity import ActorSimilarityStrategy
from ..interfaces.fallback_rules import create_fallback_system

logger = logging.getLogger(__name__)

def timed(func):
    """Decorator to log execution time of methods"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.debug(f"{func.__name__} executed in {end-start:.4f}s")
        return result
    return wrapper

class Orchestrator:
    """Orchestrates recommendation strategies with personalized weighting"""

    BASE_STRATEGY_WEIGHTS = {
        'content_based': 1.0,
        'genre_based': 0.9,
        'mood_based': 0.85,
        'actor_based': 0.8,
        'fallback': 0.5,
        'curated_fallback': 0.7
    }

    PERSONALIZATION_FACTORS = {
        'genre_strength_multiplier': 0.5,
        'mood_derivation_factor': 0.8,
        'content_reduction_factor': 0.9,
        'min_history_threshold': 5
    }

    def __init__(self):
        self.pipeline = RecommendationPipeline()
        self.watch_history = WatchHistory()
        self.affinity_model = GenreAffinityModel()
        self._user_affinity_cache = {}
        self._load_services()
        self._build_pipeline()

    @timed
    def _load_services(self) -> None:
        """Initialize all required services with lazy loading"""
        logger.info("Loading recommendation services...")
        self.genre_mappings = self._load_genre_mappings()
        self.mood_genre_map = self._build_mood_genre_map()

    @property
    @lru_cache(maxsize=1)
    def embeddings(self) -> Dict[int, np.ndarray]:
        """Cache embeddings in memory after first load"""
        try:
            with open(constants.EMBEDDINGS_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Embeddings load failed: {str(e)}")
            return {}

    @property
    @lru_cache(maxsize=1)
    def actor_similarity(self) -> Dict:
        """Cache actor data in memory after first load"""
        try:
            with open(constants.ACTOR_SIMILARITY_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Actor data load failed: {str(e)}")
            return {}

    @timed
    def _load_genre_mappings(self) -> Dict:
        """Load genre mappings from file"""
        try:
            with open(constants.GENRE_MAPPINGS_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Genre mappings load failed: {str(e)}")
            return {}

    def _build_mood_genre_map(self) -> Dict[str, List[int]]:
        """Built-in mood to genre mapping"""
        return {
            "Uplifting": [35, 10751, 10402],
            "Melancholic": [18, 36, 10749],
            "Energetic": [28, 12, 16],
            "Thoughtful": [9648, 878, 53],
            "Romantic": [10749, 35, 18]
        }

    @timed
    def _build_pipeline(self) -> None:
        """Construct the recommendation pipeline with strategies"""
        logger.info("Building recommendation pipeline...")
        
        strategies = [
            (ContentBasedStrategy(self.embeddings, logger), 'content_based'),
            (GenreRecommendationStrategy(self.genre_mappings, logger), 'genre_based'),
            (MoodRecommendationStrategy(self.mood_genre_map, self.genre_mappings, logger), 'mood_based'),
            (ActorSimilarityStrategy(self.actor_similarity, logger), 'actor_based')
        ]

        for strategy, strategy_name in strategies:
            self.pipeline.add_primary_strategy(strategy, strategy_name)

        self._setup_fallback_strategies()

    def _setup_fallback_strategies(self) -> None:
        """Configure all fallback strategies"""
        fallback_system = create_fallback_system(logger)
        
        for fallback in fallback_system:
            self.pipeline.add_fallback_strategy(
                fallback, 
                strategy_name=fallback.strategy_name
            )

    @timed
    def _get_user_affinity(self, user_id: str) -> Dict[str, Any]:
        """Get cached user affinity data with automatic refresh"""
        if user_id in self._user_affinity_cache:
            return self._user_affinity_cache[user_id]
        
        # Generate fresh affinity data
        self.watch_history.update_affinity(user_id)
        pref_vector = self.affinity_model.build_preference_vector(user_id)
        
        affinity_data = {
            'preference_vector': pref_vector,
            'top_genres': self.affinity_model.get_top_genres(user_id),
            'last_updated': datetime.now().isoformat()
        }
        
        self._user_affinity_cache[user_id] = affinity_data
        return affinity_data

    def _adjust_weights_for_user(self, user_id: Optional[str]) -> Dict[str, float]:
        """
        Dynamically adjust strategy weights based on:
        - Genre preference strength
        - Watch history volume
        - Temporal patterns
        """
        weights = self.BASE_STRATEGY_WEIGHTS.copy()
        
        if not user_id:
            return weights
            
        try:
            affinity = self._get_user_affinity(user_id)
            pref_vector = affinity['preference_vector']
            
            if not pref_vector:
                return weights
                
            # Calculate genre influence score
            genre_strength = sum(pref_vector.values())
            history_size = len(self.watch_history.get_user_history(user_id))
            
            # Only apply personalization after minimum history threshold
            if history_size >= self.PERSONALIZATION_FACTORS['min_history_threshold']:
                genre_boost = 1.0 + (
                    genre_strength * 
                    self.PERSONALIZATION_FACTORS['genre_strength_multiplier']
                )
                
                weights.update({
                    'genre_based': weights['genre_based'] * genre_boost,
                    'mood_based': weights['mood_based'] * (
                        genre_boost * 
                        self.PERSONALIZATION_FACTORS['mood_derivation_factor']
                    ),
                    'content_based': weights['content_based'] * (
                        self.PERSONALIZATION_FACTORS['content_reduction_factor']
                    )
                })
            
            logger.debug(f"Adjusted weights for {user_id}: {weights}")
            return weights
            
        except Exception as e:
            logger.error(f"Weight adjustment failed for {user_id}: {str(e)}")
            return weights

    @timed
    def get_recommendations(self, context: Dict) -> Tuple[List[Dict], Dict]:
        """
        Generate personalized recommendations with metadata
        Args:
            context: {
                'user_id': str (optional),
                'reference_movie': int,
                'mood': str (optional),
                'genres': List[str] (optional),
                'limit': int
            }
        """
        user_id = context.get('user_id')
        logger.info(f"Processing recommendations for {user_id or 'anonymous user'}")
        
        try:
            # Apply personalized weighting
            adjusted_weights = self._adjust_weights_for_user(user_id)
            self.pipeline.set_strategy_weights(adjusted_weights)
            
            # Execute pipeline
            recommendations = self.pipeline.run(context)
            recommendations_dict = [self._format_recommendation(rec) for rec in recommendations]
            
            # Generate enhanced metadata
            metadata = self._generate_metadata(recommendations, context, user_id)
            
            return recommendations_dict, metadata
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            return self._handle_failure(context)

    def _format_recommendation(self, recommendation: Recommendation) -> Dict:
        """Format recommendation with personalization context"""
        rec_dict = asdict(recommendation)
        rec_dict['score'] = rec_dict.get('score', 0) * self.BASE_STRATEGY_WEIGHTS.get(
            recommendation.source_strategy, 1.0
        )
        
        # Add personalization markers
        if recommendation.source_strategy in ('genre_based', 'mood_based'):
            rec_dict['personalization'] = {
                'type': 'genre_affinity',
                'strength': self._get_personalization_strength(
                    rec_dict.get('genres', []),
                    recommendation.user_id
                )
            }
            
        return rec_dict

    def _get_personalization_strength(self, genres: List[str], user_id: Optional[str]) -> float:
        """Calculate how strongly genres align with user preferences"""
        if not user_id or not genres:
            return 0.0
            
        try:
            affinity = self._get_user_affinity(user_id)
            return max(affinity['preference_vector'].get(g.lower(), 0) for g in genres)
        except Exception:
            return 0.0

    def _generate_metadata(self, recommendations: List[Recommendation],
                         context: Dict, user_id: Optional[str]) -> Dict:
        """Generate comprehensive metadata with personalization insights"""
        strategy_counts = defaultdict(int)
        total_score = 0.0
        
        for rec in recommendations:
            strategy_counts[rec.source_strategy] += 1
            total_score += rec.score
        
        metadata = {
            "request_context": context,
            "statistics": {
                "count": len(recommendations),
                "average_score": total_score / len(recommendations) if recommendations else 0,
                "strategy_distribution": dict(strategy_counts)
            },
            "timestamps": {
                "generated_at": datetime.now().isoformat()
            }
        }
        
        # Add personalization insights
        if user_id:
            try:
                affinity = self._get_user_affinity(user_id)
                metadata["personalization"] = {
                    "top_genres": affinity.get('top_genres', []),
                    "preference_vector": affinity.get('preference_vector', {}),
                    "history_size": len(self.watch_history.get_user_history(user_id))
                }
            except Exception as e:
                logger.error(f"Failed to generate personalization metadata: {str(e)}")
                
        return metadata

    def _handle_failure(self, context: Dict) -> Tuple[List[Dict], Dict]:
        """Execute fallback procedures with personalization context"""
        logger.warning("Initiating failure recovery procedures")
        
        fallback_recs = []
        for strategy in reversed(self.pipeline.fallback_strategies):
            try:
                if strategy.should_activate(context):
                    fallback_recs = strategy.execute(context)
                    if fallback_recs:
                        break
            except Exception as e:
                logger.error(f"Fallback strategy {strategy} failed: {str(e)}")
        
        return (
            [self._format_recommendation(r) for r in fallback_recs],
            {
                "error": "Primary strategies failed",
                "fallback_used": bool(fallback_recs)
            }
        )

# Singleton initialization
try:
    recommendation_orchestrator = Orchestrator()
    logger.info("""
        Recommendation Orchestrator initialized with:
        - Watch history integration
        - Genre affinity modeling
        - Dynamic personalization
    """)
except Exception as e:
    logger.critical(f"Orchestrator initialization failed: {str(e)}")
    raise