"""
Recommender Engine Module

This is the main entry point for the recommendation system, providing both:
1. The new pipeline-based recommendation interface
2. Backward compatibility with the legacy hybrid recommender
"""

import logging
from typing import List, Dict, Optional
from dataclasses import asdict

from .orchestrator import build_pipeline
from .strategy_interfaces.hybrid_model import (
    MovieRecommendation as LegacyMovieRec,
    HybridRecommender
)

# New pipeline system
recommendation_pipeline = build_pipeline()

# Legacy system (kept for backward compatibility)
legacy_recommender = HybridRecommender()

logger = logging.getLogger(__name__)

def get_recommendations(context: Dict) -> List[Dict]:
    """
    New unified recommendation interface using the pipeline system
    
    Args:
        context: Dictionary containing recommendation parameters including:
            - target_movie_id: Optional movie ID for similarity
            - genre_ids: List of genre IDs for filtering
            - mood: String mood name
            - limit: Maximum number of recommendations
            - user_prefs: Dictionary of user preferences
    
    Returns:
        List of recommendation dictionaries with metadata
    """
    try:
        results = recommendation_pipeline.run(context)
        return [asdict(rec) for rec in results]
    except Exception as e:
        logger.error(f"Pipeline recommendation failed: {str(e)}")
        return []

def recommend(
    target_movie_id: Optional[int] = None,
    user_mood: Optional[str] = None,
    strategy: str = "smart",
    limit: int = 10,
    user_id: Optional[str] = None,
    **kwargs
) -> List[LegacyMovieRec]:
    """
    Legacy recommendation interface maintained for backward compatibility
    
    Maps old parameters to new context format and converts results back to
    the legacy MovieRecommendation format.
    """
    try:
        # Convert legacy parameters to new context format
        context = {
            'target_movie_id': target_movie_id,
            'mood': user_mood,
            'strategy': strategy,
            'limit': limit,
            'user_id': user_id,
            **kwargs
        }
        
        # Get pipeline results
        pipeline_results = recommendation_pipeline.run(context)
        
        # Convert to legacy format
        return [
            LegacyMovieRec(
                movie_id=rec.movie_id,
                title=rec.title,
                similarity_score=rec.score,
                match_type=rec.strategy_used,
                explanation=rec.reason,
                genres=rec.metadata.get('genres', []),
                actors=rec.metadata.get('actors', []),
                poster_url=rec.metadata.get('poster_url'),
                backdrop_url=rec.metadata.get('backdrop_url')
            )
            for rec in pipeline_results
        ]
        
    except Exception as e:
        logger.warning(
            f"New pipeline failed, falling back to legacy recommender: {str(e)}"
        )
        # Fallback to legacy implementation if pipeline fails
        return legacy_recommender.recommend(
            target_movie_id=target_movie_id,
            user_mood=user_mood,
            strategy=strategy,
            limit=limit,
            user_id=user_id,
            **kwargs
        )

# Public API exports
__all__ = [
    'get_recommendations',  # New interface
    'recommend',           # Legacy interface
    'MovieRecommendation'  # Legacy data class
]

# Temporary alias for backward compatibility
MovieRecommendation = LegacyMovieRec