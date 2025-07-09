from typing import List, Dict, Optional
from dataclasses import dataclass
from service_clients.tmdb_client import TMDBClient
from core_config.constants import DEFAULT_POPULARITY_FALLBACK_LIMIT

@dataclass
class PopularMovie:
    id: int
    title: str
    popularity: float
    vote_average: float
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None

class PopularityRecommender:
    """
    Fallback recommender that provides popular movies when other methods fail.
    Integrates with the existing recommendation pipeline as a backup strategy.
    """
    
    def __init__(self, tmdb_client: TMDBClient):
        """
        Args:
            tmdb_client: Initialized TMDB client from service_clients
        """
        self.tmdb = tmdb_client
        self.min_votes_threshold = 500  # Minimum votes to be considered "popular"
        
    def get_recommendations(self, limit: int = DEFAULT_POPULARITY_FALLBACK_LIMIT) -> List[PopularMovie]:
        """
        Get currently popular movies with quality filtering.
        
        Args:
            limit: Maximum number of recommendations to return
            
        Returns:
            List of PopularMovie objects sorted by weighted score
        """
        raw_movies = self.tmdb.get_popular_movies(limit * 2)  # Get extra to filter
        
        # Filter and process results
        valid_movies = [
            PopularMovie(
                id=movie['id'],
                title=movie['title'],
                popularity=movie['popularity'],
                vote_average=movie['vote_average'],
                poster_path=movie['poster_path'],
                backdrop_path=movie['backdrop_path']
            )
            for movie in raw_movies
            if movie.get('vote_count', 0) >= self.min_votes_threshold
        ]
        
        # Score and sort by weighted popularity (60% rating, 40% raw popularity)
        scored_movies = sorted(
            valid_movies,
            key=lambda m: (m.vote_average * 0.6) + (m.popularity * 0.4),
            reverse=True
        )
        
        return scored_movies[:limit]
    
    def get_recommendations_for_movie(self, movie_id: int, limit: int = DEFAULT_POPULARITY_FALLBACK_LIMIT) -> List[PopularMovie]:
        """
        Get popular movies similar to a given movie (same primary genre)
        
        Args:
            movie_id: TMDB movie ID to use as reference
            limit: Maximum recommendations to return
            
        Returns:
            List of PopularMovie objects
        """
        try:
            movie_details = self.tmdb.get_movie_details(movie_id)
            if not movie_details or not movie_details.get('genres'):
                return self.get_recommendations(limit)
                
            primary_genre = movie_details['genres'][0]['id']
            return [
                PopularMovie(
                    id=movie['id'],
                    title=movie['title'],
                    popularity=movie['popularity'],
                    vote_average=movie['vote_average'],
                    poster_path=movie['poster_path']
                )
                for movie in self.tmdb.discover_movies(
                    with_genres=primary_genre,
                    sort_by='popularity.desc',
                    limit=limit
                )
            ]
        except Exception as e:
            # Fallback to general popular movies if any error occurs
            return self.get_recommendations(limit)
