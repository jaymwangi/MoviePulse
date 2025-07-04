# ai_smart_recommender/recommender_engine/strategy_interfaces/hybrid_model.py
"""
Hybrid Recommendation Engine

This module implements a sophisticated hybrid recommendation system that combines multiple strategies:
- Content-based filtering (via movie embeddings)
- Genre-based recommendations
- Mood-based recommendations
- Actor/director-based recommendations
- Personalized user preferences
- Fallback recommendations (via fallback_rules.py)

The system uses a weighted hybrid approach with fallback mechanisms when primary recommendations fail.
"""
import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from sklearn.metrics.pairwise import cosine_similarity
from core_config import constants
from service_clients.tmdb_client import tmdb_client
from service_clients.local_store import load_user_preferences

from .fallback_rules import FallbackRules

logger = logging.getLogger(__name__)

# ====================== Data Models ======================
@dataclass
class MovieRecommendation:
    movie_id: int
    title: str
    similarity_score: float
    match_type: str  # 'vector', 'genre', 'mood', 'actor', 'hybrid'
    explanation: str
    genres: List[str]
    actors: List[str]
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None

# ====================== Vector Similarity Service ======================
class VectorSimilarityService:
    """Content-based recommendations using movie embeddings"""
    def __init__(self):
        self.embeddings: Dict[int, np.ndarray] = {}
        self._load_embeddings()

    def _load_embeddings(self):
        """Load precomputed movie embeddings"""
        try:
            with open(constants.EMBEDDINGS_FILE, 'rb') as f:
                self.embeddings = pickle.load(f)
            logger.info(f"Loaded embeddings for {len(self.embeddings)} movies")
        except Exception as e:
            logger.error(f"Failed to load embeddings: {str(e)}")
            self.embeddings = {}

    def get_recommendations(
        self,
        target_movie_id: int,
        limit: int = 5,
        min_similarity: float = 0.3
    ) -> List[MovieRecommendation]:
        """Get recommendations using cosine similarity"""
        if target_movie_id not in self.embeddings:
            return []

        target_embedding = self.embeddings[target_movie_id].reshape(1, -1)
        all_ids = np.array(list(self.embeddings.keys()))
        all_embeddings = np.array(list(self.embeddings.values()))
        
        sim_scores = cosine_similarity(target_embedding, all_embeddings)[0]
        
        # Get top matches excluding self
        top_indices = np.argsort(sim_scores)[-limit-1:-1][::-1]
        valid_indices = [i for i in top_indices if sim_scores[i] >= min_similarity]
        
        recommendations = []
        for idx in valid_indices:
            movie_id = all_ids[idx]
            movie = tmdb_client.get_movie_details(movie_id)
            recommendations.append(MovieRecommendation(
                movie_id=movie_id,
                title=movie.title,
                similarity_score=float(sim_scores[idx]),
                match_type='vector',
                explanation="Similar content and themes",
                genres=[g.name for g in movie.genres],
                actors=[c.name for c in movie.cast[:3]],
                poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}" if movie.poster_path else None,
                backdrop_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}" if movie.backdrop_path else None
            ))
            
        return recommendations

# ====================== Genre & Mood Service ======================
class GenreMoodService:
    """Handles genre and mood-based recommendations"""
    def __init__(self):
        self.genre_mappings: Dict = {}
        self._load_genre_mappings()
        self.mood_genre_map = self._build_mood_genre_map()

    def _load_genre_mappings(self):
        """Load movie to genre mappings"""
        try:
            with open(constants.GENRE_MAPPINGS_FILE, 'r') as f:
                self.genre_mappings = json.load(f)
            logger.info(f"Loaded genre mappings for {len(self.genre_mappings)} movies")
        except Exception as e:
            logger.error(f"Failed to load genre mappings: {str(e)}")
            self.genre_mappings = {}

    def _build_mood_genre_map(self) -> Dict[str, List[int]]:
        """Map moods to relevant genres"""
        return {
            "Uplifting": [35, 10751, 10402],  # Comedy, Family, Music
            "Melancholic": [18, 36, 10749],   # Drama, History, Romance
            "Exciting": [28, 12, 53],         # Action, Adventure, Thriller
            "Romantic": [10749, 35],          # Romance, Comedy
            "Chill": [35, 10402, 10751],      # Comedy, Music, Family
            "Suspenseful": [53, 9648, 80],    # Thriller, Mystery, Crime
            "Dark": [27, 80, 9648],           # Horror, Crime, Mystery
            "Empowering": [18, 28, 37],       # Drama, Action, Western
            "Whimsical": [16, 14, 10751],    # Animation, Fantasy, Family
            "Thought-Provoking": [878, 18, 36] # Sci-Fi, Drama, History
        }

    def get_genre_recommendations(
        self,
        target_genre_ids: List[int],
        limit: int = 5
    ) -> List[MovieRecommendation]:
        """Get recommendations based on genre similarity"""
        target_genres = set(str(g_id) for g_id in target_genre_ids)
        scored_movies = []
        
        for movie_id, data in self.genre_mappings.items():
            movie_genres = set(data.get('genre_ids', []))
            overlap = movie_genres & target_genres
            if overlap:
                score = len(overlap) / len(target_genres)
                scored_movies.append((int(movie_id), score))
        
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        return self._format_recommendations(scored_movies[:limit], "genre")

    def get_mood_recommendations(
        self,
        mood_name: str,
        limit: int = 5
    ) -> List[MovieRecommendation]:
        """Get recommendations based on mood"""
        genre_ids = self.mood_genre_map.get(mood_name, [])
        if not genre_ids:
            return []
        return self.get_genre_recommendations(genre_ids, limit)

    def _format_recommendations(
        self,
        movie_scores: List[Tuple[int, float]],
        match_type: str
    ) -> List[MovieRecommendation]:
        """Format raw movie scores into recommendations"""
        recommendations = []
        for movie_id, score in movie_scores:
            movie = tmdb_client.get_movie_details(movie_id)
            recommendations.append(MovieRecommendation(
                movie_id=movie_id,
                title=movie.title,
                similarity_score=score,
                match_type=match_type,
                explanation=f"Matched by {match_type} compatibility",
                genres=[g.name for g in movie.genres],
                actors=[c.name for c in movie.cast[:3]],
                poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}" if movie.poster_path else None,
                backdrop_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}" if movie.backdrop_path else None
            ))
        return recommendations

# ====================== Actor Similarity Service ======================
class ActorSimilarityService:
    """Handles actor-based recommendations"""
    def __init__(self):
        self.similarity_data: Dict = {}
        self._load_data()

    def _load_data(self):
        """Load actor similarity data"""
        try:
            with open(constants.ACTOR_SIMILARITY_FILE, "r") as f:
                self.similarity_data = json.load(f)
            logger.info(f"Loaded actor similarity data for {len(self.similarity_data)} actors")
        except Exception as e:
            logger.error(f"Failed to load actor similarity data: {str(e)}")
            self.similarity_data = {}

    def get_actor_recommendations(
        self,
        target_actor_ids: List[int],
        limit: int = 5
    ) -> List[MovieRecommendation]:
        """Get recommendations based on actor similarity"""
        similar_movies = set()
        
        for actor_id in target_actor_ids:
            actor_data = self.similarity_data.get(str(actor_id), {})
            for similar in actor_data.get("similar_actors", [])[:5]:
                actor_movies = tmdb_client.get_actor_filmography(similar["actor_id"])
                similar_movies.update(m.id for m in actor_movies)
        
        return self._format_recommendations(list(similar_movies)[:limit], "actor")

    def _format_recommendations(
        self,
        movie_ids: List[int],
        match_type: str
    ) -> List[MovieRecommendation]:
        """Format movie IDs into recommendations"""
        recommendations = []
        for movie_id in movie_ids:
            movie = tmdb_client.get_movie_details(movie_id)
            recommendations.append(MovieRecommendation(
                movie_id=movie_id,
                title=movie.title,
                similarity_score=0.7,  # Default score for actor matches
                match_type=match_type,
                explanation="Recommended because you like similar actors",
                genres=[g.name for g in movie.genres],
                actors=[c.name for c in movie.cast[:3]],
                poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}" if movie.poster_path else None,
                backdrop_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}" if movie.backdrop_path else None
            ))
        return recommendations

# ====================== Enhanced Hybrid Recommender ======================
class EnhancedHybridRecommender:
    """Orchestrates multiple recommendation strategies with personalization"""
    def __init__(self):
        self.vector_service = VectorSimilarityService()
        self.genre_service = GenreMoodService()
        self.actor_service = ActorSimilarityService()
        self.user_prefs = load_user_preferences()
        self.fallback_rules = FallbackRules()  
        self._initialize_fallback_system() 

    def _initialize_fallback_system(self):
        """Initialize the fallback recommendation system"""
        try:
            self.fallback_rules.load_all(
                Path(constants.GENRES_FILE),
                Path(constants.MOODS_FILE)
            )
            logger.info("Fallback rules system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize fallback system: {str(e)}")

    def recommend(
        self,
        target_movie_id: Optional[int] = None,
        user_mood: Optional[str] = None,
        strategy: str = "smart",  # 'smart', 'vector', 'genre', 'mood', 'actor'
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[MovieRecommendation]:
        """Main recommendation interface with personalization"""
        # Load user preferences if available
        user_prefs = self.user_prefs.get(user_id, {}) if user_id else {}
        
        recommendations = []
        
        # 1. Content-based (vector similarity)
        if target_movie_id and strategy in ("smart", "vector"):
            vector_recs = self.vector_service.get_recommendations(
                target_movie_id,
                limit=limit,
                min_similarity=0.3
            )
            recommendations.extend(vector_recs)
        # 2. Genre-based (from target movie or user prefs)
        if strategy in ("smart", "genre"):
            genre_ids = []
            if target_movie_id:
                movie = tmdb_client.get_movie_details(target_movie_id)
                if movie and getattr(movie, "genres", None):
                    genre_ids = [g.id for g in movie.genres]
                else:
                    logger.warning(
                        f"Could not load genres for movie ID {target_movie_id}. Skipping genre-based fallback."
                    )
            elif user_prefs.get("preferred_genres"):
                genre_ids = user_prefs["preferred_genres"]

            if genre_ids:
                genre_recs = self.genre_service.get_genre_recommendations(
                    genre_ids,
                    limit=limit // 2
                )
                recommendations.extend(genre_recs)

        
        # 3. Mood-based (explicit or from user prefs)
        if strategy in ("smart", "mood"):
            effective_mood = user_mood or user_prefs.get("preferred_moods", [None])[0]
            if effective_mood:
                mood_recs = self.genre_service.get_mood_recommendations(effective_mood, limit//2)
                recommendations.extend(mood_recs)
        
        # 4. Actor-based (from user prefs)
        if strategy in ("smart", "actor") and user_prefs.get("preferred_actors"):
            actor_recs = self.actor_service.get_actor_recommendations(
                user_prefs["preferred_actors"],
                limit=limit//3
            )
            recommendations.extend(actor_recs)

         # Add fallback recommendations if primary methods return few results
        if len(recommendations) < limit//2:
            fallback_recs = self._get_fallback_recommendations(
                target_movie_id,
                user_mood,
                user_prefs,
                max(limit//2, limit - len(recommendations))
            )
            recommendations.extend(fallback_recs)
        
        # Process and return final recommendations
        unique_recs = self._deduplicate_recommendations(recommendations)
        scored_recs = self._apply_user_preferences(unique_recs, user_prefs)
        return scored_recs[:limit]

    def _deduplicate_recommendations(
        self,
        recs: List[MovieRecommendation]
    ) -> List[MovieRecommendation]:
        """Deduplicate movie recommendations but merge their explanations"""
        merged = {}
        for rec in recs:
            if rec.movie_id in merged:
                # merge explanations
                existing = merged[rec.movie_id]
                explanations = set(existing.explanation.split(" / ")) | set(rec.explanation.split(" / "))
                existing.explanation = " / ".join(sorted(explanations))
            else:
                merged[rec.movie_id] = rec
        return list(merged.values())


    def _apply_user_preferences(
        self,
        recs: List[MovieRecommendation],
        prefs: Dict
    ) -> List[MovieRecommendation]:
        """Adjust scores based on user preferences"""
        preferred_genres = set(prefs.get("preferred_genres", []))
        disliked_genres = set(prefs.get("disliked_genres", []))
        preferred_moods = [m.lower() for m in prefs.get("preferred_moods", [])]
        
        # Create a dictionary to store the highest score for each movie
        movie_scores = {}
        
        for rec in recs:
            # Skip if we've already processed this movie with a higher score
            if rec.movie_id in movie_scores and movie_scores[rec.movie_id] >= rec.similarity_score:
                continue
                
            new_score = rec.similarity_score
            
            # Apply dislike penalty first (50% reduction if any disliked genre)
            if any(g in disliked_genres for g in rec.genres):
                new_score *= 0.5
            else:
                # Apply single 10% boost if ANY preferred genre matches
                if any(g in preferred_genres for g in rec.genres):
                    new_score *= 1.1
                    
                # Apply mood boost (50% if mood matches) 
                if any(m in rec.explanation.lower() for m in preferred_moods):
                    new_score *= 1.5
            
            movie_scores[rec.movie_id] = new_score
        import copy

        
        # Convert back to list of recommendations with updated scores
        result = []
        for rec in recs:
            if rec.movie_id in movie_scores:
                new_rec = copy.deepcopy(rec)
                new_rec.similarity_score = movie_scores[rec.movie_id]
                result.append(new_rec)
        
        return sorted(result, key=lambda x: x.similarity_score, reverse=True)

    def _get_fallback_recommendations(
        self,
        target_movie_id: Optional[int],
        user_mood: Optional[str],
        user_prefs: Dict,
        limit: int
    ) -> List[MovieRecommendation]:
        """Generate fallback recommendations with empty input handling"""
        try:
            # Get genres - convert to list of IDs
            genre_ids = []
            if target_movie_id:
                movie = tmdb_client.get_movie_details(target_movie_id)
                genre_ids = [g.id for g in getattr(movie, 'genres', [])]
            elif user_prefs.get("preferred_genres"):
                genre_ids = user_prefs["preferred_genres"]
            
            # Get moods - convert to list of IDs
            mood_ids = []
            effective_mood = user_mood or user_prefs.get("preferred_moods", [None])[0]
            if effective_mood and hasattr(self.fallback_rules, 'moods'):
                mood_ids = [
                    m.id for m in self.fallback_rules.moods.values() 
                    if m.name.lower() == effective_mood.lower()
                ]
            
            # Get compatible movies (FallbackRules handles empty inputs)
            compatible_movies = self.fallback_rules.get_compatible_movies(
                genre_ids or None,
                mood_ids or None
            ) or []
            
            # Format recommendations
            return self._format_fallback_recommendations(compatible_movies[:limit])
        
        except Exception as e:
            logger.warning(f"Fallback recommendation failed: {str(e)}")
            return []

    def _format_fallback_recommendations(self, movie_ids: List[int]) -> List[MovieRecommendation]:
        """Format fallback recommendations with error handling"""
        recommendations = []
        for movie_id in movie_ids:
            try:
                movie = tmdb_client.get_movie_details(movie_id)
                if movie:
                    recommendations.append(MovieRecommendation(
                        movie_id=movie_id,
                        title=getattr(movie, 'title', 'Unknown'),
                        similarity_score=0.6,
                        match_type='fallback',
                        explanation="Recommended through fallback rules",
                        genres=[g.name for g in getattr(movie, 'genres', [])],
                        actors=[c.name for c in getattr(movie, 'cast', [])[:3]],
                        poster_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.poster_path}" if getattr(movie, 'poster_path', None) else None,
                        backdrop_url=f"{constants.TMDB_IMAGE_BASE_URL}{movie.backdrop_path}" if getattr(movie, 'backdrop_path', None) else None
                    ))
            except Exception as e:
                logger.warning(f"Failed to format movie {movie_id}: {str(e)}")
        
        return recommendations
# ====================== Singleton Instance ======================
hybrid_recommender = EnhancedHybridRecommender()