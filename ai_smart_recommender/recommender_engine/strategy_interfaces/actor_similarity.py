"""
Actor Similarity Recommendation Engine

This module implements actor-based recommendations using:
- Actor similarity graphs
- Co-star analysis
- Director-actor collaborations
"""

import json
from typing import List, Dict, Optional,Any
import logging
from dataclasses import dataclass

from core_config import constants
from service_clients.tmdb_client import tmdb_client

logger = logging.getLogger(__name__)

@dataclass
class ActorRecommendation:
    actor_id: int
    name: str
    similarity_score: float
    movies_in_common: List[int]
    explanation: str

@dataclass
class MovieRecommendation:
    movie_id: int
    title: str
    similarity_score: float
    match_type: str  # 'actor' or 'co-star'
    explanation: str
    genres: List[str]
    actors: List[str]
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None



class ActorSimilarityService:
    """Handles actor-based recommendations with similarity graphs"""

    def __init__(self, similarity_data: Dict, logger: Optional[logging.Logger] = None):
        self.similarity_data: Dict = similarity_data
        self.logger = logger or logging.getLogger(__name__)


    def get_similar_actors(
        self, 
        target_actor_id: int,
        limit: int = 5
    ) -> List[ActorRecommendation]:
        """Get similar actors based on precomputed similarity graph"""
        actor_data = self.similarity_data.get(str(target_actor_id))
        if not actor_data:
            return []

        similar_actors = []
        for similar in actor_data.get("similar_actors", [])[:limit]:
            similar_actors.append(ActorRecommendation(
                actor_id=similar["actor_id"],
                name=self._get_actor_name(similar["actor_id"]),
                similarity_score=similar["score"],
                movies_in_common=similar["common_movies"],
                explanation=f"Worked together in {len(similar['common_movies'])} movies"
            ))
        
        return similar_actors

    def get_actor_recommendations(
        self,
        target_actor_ids: List[int],
        limit: int = 5
    ) -> List[MovieRecommendation]:
        """Get movie recommendations based on actor similarity"""
        similar_movies = set()
        
        for actor_id in target_actor_ids:
            actor_data = self.similarity_data.get(str(actor_id), {})
            for similar in actor_data.get("similar_actors", [])[:5]:
                actor_movies = tmdb_client.get_actor_filmography(similar["actor_id"])
                similar_movies.update(m.id for m in actor_movies)
        
        return self._format_recommendations(list(similar_movies)[:limit])

    def _get_actor_name(self, actor_id: int) -> str:
        """Get actor name from TMDB or cache"""
        try:
            actor = tmdb_client.get_actor_details(actor_id)
            return actor.name if actor else f"Actor_{actor_id}"
        except Exception:
            return f"Actor_{actor_id}"

    def _format_recommendations(
        self,
        movie_ids: List[int]
    ) -> List[MovieRecommendation]:
        """Format movie IDs into recommendations"""
        recommendations = []
        for movie_id in movie_ids:
            movie = tmdb_client.get_movie_details(movie_id)
            recommendations.append(MovieRecommendation(
                movie_id=movie_id,
                title=movie.title,
                similarity_score=0.7,  # Default score for actor matches
                match_type='actor',
                explanation="Recommended because you like similar actors",
                genres=[g.name for g in movie.genres],
                actors=[c.name for c in movie.cast[:3]],
                poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}" if movie.poster_path else None,
                backdrop_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}" if movie.backdrop_path else None
            ))
        return recommendations
    
from ai_smart_recommender.interfaces.base_recommender import BaseRecommender, Recommendation

class ActorSimilarityStrategy(BaseRecommender):
    """Wrapper that plugs actor similarity service into the recommender pipeline"""

    def __init__(self, similarity_data: Dict, logger: Optional[logging.Logger] = None):
        self._service = ActorSimilarityService(similarity_data, logger or logging.getLogger(__name__))
        self.logger = logger or logging.getLogger(__name__)

    @property
    def strategy_name(self) -> str:
        return "actor_based"

    def execute(self, context: Dict[str, Any]) -> List[Recommendation]:
        actor_ids = context.get("preferred_actors") or context.get("actor_ids", [])
        if not actor_ids:
            return []

        limit = context.get("limit", 5)
        movie_recs = self._service.get_actor_recommendations(actor_ids, limit)

        return [
            Recommendation(
                movie_id=rec.movie_id,
                title=rec.title,
                score=rec.similarity_score,
                reason=rec.explanation,
                strategy_used=self.strategy_name,
                metadata={
                    "match_type": rec.match_type,
                    "genres": rec.genres,
                    "actors": rec.actors,
                    "poster_url": rec.poster_url,
                    "backdrop_url": rec.backdrop_url
                }
            )
            for rec in movie_recs
        ]
