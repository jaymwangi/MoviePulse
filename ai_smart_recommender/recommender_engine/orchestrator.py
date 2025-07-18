"""
Enhanced Recommendation Pipeline Orchestrator

Key Improvements:
1. Injected logging into all strategies
2. Added recommendation metadata
3. Lazy loading for large files with caching
4. Strategy weighting system
5. Performance timing decorators
6. Full fallback pipeline including curated sets
"""

import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging
from functools import lru_cache, wraps
import time
from dataclasses import asdict

# Shared modules
from core_config import constants
from service_clients import tmdb_client

# Interfaces
from ..interfaces.base_recommender import Recommendation
from ..rec_pipeline import RecommendationPipeline

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
    """Enhanced orchestrator with performance optimizations and better observability"""

    STRATEGY_WEIGHTS = {
        'content_based': 1.0,
        'genre_based': 0.9,
        'mood_based': 0.85,
        'actor_based': 0.8,
        'fallback': 0.5,
        'curated_fallback': 0.7  # Higher weight than regular fallbacks
    }

    def __init__(self):
        self.pipeline = RecommendationPipeline()
        self._load_services()
        self._build_pipeline()

    @timed
    def _load_services(self) -> None:
        """Lazy load all required data services with caching"""
        logger.info("Loading recommendation services...")
        self.genre_mappings = self._load_genre_mappings()
        self.mood_genre_map = self._build_mood_genre_map()
        # Large files loaded only when needed via properties

    @property
    @lru_cache(maxsize=1)
    def embeddings(self) -> Dict[int, np.ndarray]:
        """Cache embeddings in memory after first load"""
        return self._load_embeddings()

    @property
    @lru_cache(maxsize=1)
    def actor_similarity(self) -> Dict:
        """Cache actor data in memory after first load"""
        return self._load_actor_similarity()

    @timed
    def _load_embeddings(self) -> Dict[int, np.ndarray]:
        """Actual embeddings loader"""
        try:
            with open(constants.EMBEDDINGS_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Embeddings load failed: {str(e)}")
            return {}

    @timed
    def _load_genre_mappings(self) -> Dict:
        """Load genre mappings"""
        try:
            with open(constants.GENRE_MAPPINGS_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Genre mappings load failed: {str(e)}")
            return {}

    @timed
    def _load_actor_similarity(self) -> Dict:
        """Load actor similarity data"""
        try:
            with open(constants.ACTOR_SIMILARITY_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Actor data load failed: {str(e)}")
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
        """Construct pipeline with weighted strategies"""
        logger.info("Building recommendation pipeline...")
        
        # Primary strategies with injected logger and weights
        strategies = [
            (ContentBasedStrategy(self.embeddings, logger), self.STRATEGY_WEIGHTS['content_based']),
            (GenreRecommendationStrategy(self.genre_mappings, logger), self.STRATEGY_WEIGHTS['genre_based']),
            (MoodRecommendationStrategy(self.mood_genre_map, self.genre_mappings, logger), self.STRATEGY_WEIGHTS['mood_based']),
            (ActorSimilarityStrategy(self.actor_similarity, logger), self.STRATEGY_WEIGHTS['actor_based'])
        ]

        for strategy, weight in strategies:
            self.pipeline.add_primary_strategy(strategy, weight=weight)

        # Enhanced fallback system with curated support
        self._setup_fallback_strategies()

    def _setup_fallback_strategies(self) -> None:
        """Configure all fallback strategies with proper weighting"""
        fallback_system = create_fallback_system(logger)
        
        for fallback in fallback_system:
            weight = self.STRATEGY_WEIGHTS.get(
                fallback.strategy_name, 
                self.STRATEGY_WEIGHTS['fallback']
            )
            self.pipeline.add_fallback_strategy(fallback, weight=weight)
            
            # Special handling for curated fallback
            if fallback.strategy_name == "curated_fallback":
                logger.info("Curated fallback strategy registered")

    @timed
    def get_recommendations(self, context: Dict) -> Tuple[List[Dict], Dict]:
        """
        Enhanced recommendation interface with metadata
        
        Returns:
            Tuple of (recommendations, metadata)
        """
        logger.info(f"Processing recommendation request: {context.get('request_id', 'no-request-id')}")
        
        # Set fallback flag if primary strategies fail
        context.setdefault('fallback_required', False)
        
        try:
            recommendations = self.pipeline.run(context)
            recommendations_dict = [self._format_recommendation(rec) for rec in recommendations]
            
            metadata = self._generate_metadata(recommendations, context)
            
            return recommendations_dict, metadata
        except Exception as e:
            logger.error(f"Recommendation failed: {str(e)}")
            return self._handle_failure(context)

    def _format_recommendation(self, recommendation: Recommendation) -> Dict:
        """Apply formatting and weights to recommendation"""
        rec_dict = asdict(recommendation)
        
        # Apply strategy-specific weighting
        strategy_weight = self.STRATEGY_WEIGHTS.get(
            recommendation.source_strategy, 
            1.0
        )
        rec_dict['similarity_score'] *= strategy_weight
        
        # Add additional metadata for curated sets
        if recommendation.source_strategy == "curated_fallback":
            rec_dict['is_curated'] = True
            rec_dict['special_tag'] = recommendation.metadata.get('set_name', 'Curated Selection')
        
        return rec_dict

    def _generate_metadata(self, recommendations: List[Recommendation], context: Dict) -> Dict:
        """Generate comprehensive metadata about the recommendation process"""
        strategies_used = {rec.source_strategy for rec in recommendations}
        
        return {
            "strategies_used": list(strategies_used),
            "recommendation_count": len(recommendations),
            "fallback_used": any(rec.is_fallback for rec in recommendations),
            "curated_used": any(rec.source_strategy == "curated_fallback" for rec in recommendations),
            "context_summary": {
                k: v for k, v in context.items() 
                if k not in ['user_prefs', 'explicit_filters']
            },
            "performance_metrics": {
                "average_score": sum(rec.similarity_score for rec in recommendations) / len(recommendations) if recommendations else 0,
                "strategy_distribution": {
                    strategy: sum(1 for rec in recommendations if rec.source_strategy == strategy)
                    for strategy in strategies_used
                }
            }
        }

    def _handle_failure(self, context: Dict) -> Tuple[List[Dict], Dict]:
        """Handle complete recommendation failure with last-resort fallback"""
        logger.warning("All strategies failed - attempting emergency fallback")
        
        # Try to get any recommendations from the last fallback
        last_resort_recs = []
        for fallback in reversed(self.pipeline.fallback_strategies):
            try:
                if fallback.should_activate(context):
                    last_resort_recs = fallback.execute(context)
                    if last_resort_recs:
                        break
            except Exception as e:
                logger.error(f"Emergency fallback failed: {str(e)}")
        
        formatted_recs = [self._format_recommendation(rec) for rec in last_resort_recs]
        metadata = {
            "error": "Primary strategies failed",
            "fallback_used": bool(last_resort_recs),
            "recommendation_count": len(last_resort_recs)
        }
        
        return formatted_recs, metadata

# Singleton with initialization logging
try:
    recommendation_orchestrator = Orchestrator()
    logger.info("Recommendation orchestrator initialized successfully")
except Exception as e:
    logger.critical(f"Orchestrator failed to initialize: {str(e)}")
    raise

def build_pipeline() -> Orchestrator:
    """Factory method for pipeline construction"""
    return Orchestrator()