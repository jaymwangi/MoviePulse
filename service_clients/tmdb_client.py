"""
TMDB API Client with Advanced Hybrid Filtering
---------------------------------------------
Features:
- Smart search with configurable fallback strategies
- Server-side and client-side filtering
- Comprehensive error handling
- Full type hints and documentation
"""

import os
from pathlib import Path
import requests
from typing import Optional, List, Dict, Tuple
from tenacity import retry, wait_exponential, stop_after_attempt
from core_config.constants import Movie, Person, Genre,Video
import streamlit as st
from datetime import datetime
from enum import Enum, auto

class FallbackStrategy(Enum):
    NONE = auto()
    RELAX_ALL = auto()
    RELAX_GRADUAL = auto()
    RELAX_RATING_FIRST = auto()
    RELAX_GENRE_FIRST = auto()

class TMDBClient:
    def __init__(self):
        """Initialize TMDB client with API key from .env or Streamlit secrets."""
        self.api_key = self._get_api_key()
        if not self.api_key:
            raise RuntimeError("TMDB_API_KEY not found in environment variables or secrets")
        
        self.base_url = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        self.default_timeout = 10

    def _get_api_key(self) -> Optional[str]:
        """Retrieve API key from environment or Streamlit secrets."""
        # Try .env file in current or parent directories
        for level in range(4):
            env_path = Path(__file__).resolve().parents[level] / ".env"
            if env_path.exists():
                from dotenv import load_dotenv
                load_dotenv(env_path)
                if api_key := os.getenv("TMDB_API_KEY"):
                    return api_key
        
        # Fallback to Streamlit secrets
        try:
            return st.secrets.get("TMDB_API_KEY")
        except Exception:
            return None

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10),
           stop=stop_after_attempt(3))
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Dict:
        """Make authenticated request to TMDB API with retry logic."""
        params = params or {}
        params.update({"api_key": self.api_key})
        
        try:
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=self.default_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            raise

    def _validate_filters(self, filters: Dict) -> Dict:
        """Ensure filter values are within valid ranges."""
        if not filters:
            return {}
            
        validated = {}
        current_year = datetime.now().year
        
        # Validate year range
        if "year_range" in filters:
            try:
                start, end = filters["year_range"]
                validated["year_range"] = (
                    max(1900, min(start, current_year)),
                    min(current_year + 5, max(end, start))
                )
            except (TypeError, ValueError):
                st.warning("Invalid year range format, ignoring")
        
        # Validate rating
        if "min_rating" in filters:
            try:
                validated["min_rating"] = max(0.0, min(10.0, float(filters["min_rating"])))
            except (TypeError, ValueError):
                st.warning("Invalid rating value, ignoring")
        
        # Genres are validated separately in _get_genre_ids_by_names
        if "genres" in filters:
            validated["genres"] = filters["genres"]
            
        return validated

    def search_movies(
        self,
        query: str,
        filters: Optional[Dict] = None,
        fallback_strategy: FallbackStrategy = FallbackStrategy.RELAX_GRADUAL,
        page: int = 1
    ) -> Tuple[List[Movie], int]:
        """Search movies with hybrid filtering capabilities."""
        validated_filters = self._validate_filters(filters) if filters else None
        params = self._build_search_params(query, validated_filters, page)

        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_search(p: Dict) -> Dict:
            return self._make_request("search/movie", p)

        try:
            with st.spinner(f"Searching '{query}'..."):
                data = _cached_search(params)

            if not data.get("results") and validated_filters and fallback_strategy != FallbackStrategy.NONE:
                return self._handle_empty_results(
                    query=query,
                    original_params=params,
                    original_filters=validated_filters,
                    strategy=fallback_strategy,
                    page=page
                )

            movies = [self._parse_movie_result(m) for m in data.get("results", [])]
            return movies, data.get("total_pages", 1)

        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            return [], 0

    def _build_search_params(
        self,
        query: str,
        filters: Optional[Dict],
        page: int
    ) -> Dict:
        """Construct search parameters dictionary."""
        params = {
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": "en-US"
        }
        
        if not filters:
            return params
            
        # Apply genre filter
        if filters.get("genres"):
            if genre_ids := self._get_genre_ids_by_names(filters["genres"]):
                params["with_genres"] = ",".join(map(str, genre_ids))
        
        # Apply year range filter
        if filters.get("year_range"):
            start, end = filters["year_range"]
            params.update({
                "primary_release_date.gte": f"{start}-01-01",
                "primary_release_date.lte": f"{end}-12-31"
            })
        
        # Apply rating filter
        if filters.get("min_rating"):
            params["vote_average.gte"] = filters["min_rating"]
            
        return params

    def _handle_empty_results(
        self,
        query: str,
        original_params: Dict,
        original_filters: Dict,
        strategy: FallbackStrategy,
        page: int
    ) -> Tuple[List[Movie], int]:
        """Execute fallback strategy when no results are found."""
        if strategy == FallbackStrategy.RELAX_ALL:
            return self._relax_all_filters(query, page)
            
        elif strategy in (FallbackStrategy.RELAX_GRADUAL, FallbackStrategy.RELAX_RATING_FIRST, 
                         FallbackStrategy.RELAX_GENRE_FIRST):
            return self._gradual_relaxation(
                query=query,
                original_params=original_params,
                original_filters=original_filters,
                strategy=strategy,
                page=page
            )
            
        return [], 0

    def _relax_all_filters(
        self,
        query: str,
        page: int
    ) -> Tuple[List[Movie], int]:
        """Remove all filters and retry search."""
        params = {
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": "en-US"
        }
        
        try:
            data = self._make_request("search/movie", params)
            st.warning("No results with filters - showing unfiltered results")
            return [self._parse_movie_result(m) for m in data.get("results", [])], data.get("total_pages", 1)
        except Exception:
            return [], 0

    def _gradual_relaxation(
        self,
        query: str,
        original_params: Dict,
        original_filters: Dict,
        strategy: FallbackStrategy,
        page: int
    ) -> Tuple[List[Movie], int]:
        """Gradually relax filters based on strategy."""
        relaxation_steps = self._get_relaxation_steps(strategy)
        
        for step in relaxation_steps:
            if not any(f in original_filters for f in step["filters"]):
                continue
                
            params = original_params.copy()
            for key in step["remove_params"]:
                params.pop(key, None)
            
            try:
                data = self._make_request("search/movie", params)
                if data.get("results"):
                    st.warning(step["message"])
                    return (
                        [self._parse_movie_result(m) for m in data["results"]],
                        data.get("total_pages", 1)
                    )
            except Exception:
                continue
                
        return [], 0

    def _get_relaxation_steps(self, strategy: FallbackStrategy) -> List[Dict]:
        """Get relaxation steps based on strategy."""
        base_steps = [
            {
                "filters": ["min_rating"],
                "remove_params": ["vote_average.gte"],
                "message": "Relaxed rating filter"
            },
            {
                "filters": ["year_range"],
                "remove_params": ["primary_release_date.gte", "primary_release_date.lte"],
                "message": "Relaxed year range filter"
            },
            {
                "filters": ["genres"],
                "remove_params": ["with_genres"],
                "message": "Relaxed genre filter"
            }
        ]
        
        if strategy == FallbackStrategy.RELAX_RATING_FIRST:
            return base_steps
        elif strategy == FallbackStrategy.RELAX_GENRE_FIRST:
            return [base_steps[2], base_steps[0], base_steps[1]]
        else:  # Default gradual
            return base_steps


    def get_trending_movies(
        self,
        time_window: str = "week",
        filters: Optional[Dict] = None,
        fallback_strategy: FallbackStrategy = FallbackStrategy.RELAX_GRADUAL
    ) -> List[Movie]:
        """Get trending movies with client-side filtering."""
        if time_window not in ("day", "week"):
            raise ValueError("time_window must be 'day' or 'week'")

        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_trending_fetch(window: str) -> Dict:
            return self._make_request(f"trending/movie/{window}")

        try:
            with st.spinner("Loading trending movies..."):
                data = _cached_trending_fetch(time_window)

            movies = [self._parse_movie_result(m) for m in data.get("results", [])]

            if filters:
                movies = self._filter_movies_client_side(
                    movies=movies,
                    filters=filters,
                    strategy=fallback_strategy
                )

            return movies
        except Exception as e:
            st.error(f"Failed to load trending movies: {str(e)}")
            return []

    def _filter_movies_client_side(
        self,
        movies: List[Movie],
        filters: Dict,
        strategy: FallbackStrategy
    ) -> List[Movie]:
        """Apply client-side filtering with fallback."""
        validated_filters = self._validate_filters(filters)
        filtered = self._apply_filters(movies, validated_filters)
        
        if not filtered and strategy != FallbackStrategy.NONE:
            if strategy == FallbackStrategy.RELAX_ALL:
                st.warning("No matches with filters - showing all trending movies")
                return movies
                
            return self._gradual_client_side_relaxation(movies, validated_filters, strategy)
            
        return filtered

    def _gradual_client_side_relaxation(
        self,
        movies: List[Movie],
        filters: Dict,
        strategy: FallbackStrategy
    ) -> List[Movie]:
        """Gradually relax client-side filters."""
        relaxation_order = self._get_client_side_relaxation_order(strategy)
        
        for filter_key in relaxation_order:
            if filter_key not in filters:
                continue
                
            relaxed_filters = filters.copy()
            relaxed_filters.pop(filter_key)
            filtered = self._apply_filters(movies, relaxed_filters)
            
            if filtered:
                st.warning(f"Relaxed {filter_key} filter")
                return filtered
                
        return []

    def _get_client_side_relaxation_order(self, strategy: FallbackStrategy) -> List[str]:
        """Get relaxation order for client-side filtering."""
        if strategy == FallbackStrategy.RELAX_RATING_FIRST:
            return ["min_rating", "year_range", "genres"]
        elif strategy == FallbackStrategy.RELAX_GENRE_FIRST:
            return ["genres", "min_rating", "year_range"]
        else:  # Default gradual
            return ["min_rating", "year_range", "genres"]

    def _apply_filters(self, movies: List[Movie], filters: Dict) -> List[Movie]:
        """Apply filters to a list of movies."""
        if not filters:
            return movies
            
        filtered = movies.copy()
        
        # Genre filter
        if filters.get("genres"):
            genre_ids = self._get_genre_ids_by_names(filters["genres"])
            if genre_ids:
                filtered = [m for m in filtered if any(g.id in genre_ids for g in m.genres)]
        
        # Year range filter
        if filters.get("year_range"):
            start, end = filters["year_range"]
            filtered = [
                m for m in filtered
                if m.release_date and start <= int(m.release_date[:4]) <= end
            ]
        
        # Rating filter
        if filters.get("min_rating"):
            min_rating = float(filters["min_rating"])
            filtered = [m for m in filtered if m.vote_average >= min_rating]
            
        return filtered


    def get_movie_details(self, movie_id: int) -> Movie:
        """Get complete movie details with credits."""

        @st.cache_data(ttl=86400, show_spinner=False)
        def _cached_movie_details_fetch(mid: int) -> Dict:
            return self._make_request(
                f"movie/{mid}",
                {"append_to_response": "credits,similar"}
            )

        try:
            data = _cached_movie_details_fetch(movie_id)
            return self._parse_movie_result(data, full_details=True)
        except Exception as e:
            st.error(f"Failed to load movie details: {str(e)}")
            raise


    def get_genres(self) -> List[Genre]:
        """Get all movie genres."""

        @st.cache_data(ttl=86400 * 7)
        def _cached_genre_fetch() -> Dict:
            return self._make_request("genre/movie/list")

        try:
            data = _cached_genre_fetch()
            return [Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])]
        except Exception as e:
            st.error(f"Failed to load genres: {str(e)}")
            return []
        
    def _get_genre_ids_by_names(self, genre_names: List[str]) -> List[int]:
        """Convert genre names to IDs."""
        all_genres = self.get_genres()
        name_to_id = {g.name.lower(): g.id for g in all_genres}
        
        ids = []
        for name in genre_names:
            lower_name = name.lower()
            if lower_name in name_to_id:
                ids.append(name_to_id[lower_name])
            else:
                st.warning(f"Ignoring unknown genre: {name}")
        
        return ids

    def _parse_movie_result(self, data: Dict, full_details: bool = False) -> Movie:
        """Convert TMDB API response to Movie object."""
        return Movie(
            id=data.get("id", 0),
            title=data.get("title", "Untitled"),
            overview=data.get("overview", ""),
            release_date=data.get("release_date", ""),
            poster_path=data.get("poster_path", ""),
            vote_average=data.get("vote_average", 0),
            genres=[Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])],
            directors=[
                Person(id=p["id"], name=p["name"], role="Director")
                for p in data.get("credits", {}).get("crew", [])
                if p.get("job") == "Director"
            ] if full_details else [],
            cast=[
                Person(id=p["id"], name=p["name"], role=p.get("character", "Actor"),
                profile_path=p.get("profile_path"))
                for p in data.get("credits", {}).get("cast", [])[:10]
            ] if full_details else [],
            similar_movies=[
                self._parse_movie_result(m)
                for m in data.get("similar", {}).get("results", [])[:5]
            ] if full_details else []
        )
    
    @st.cache_data(ttl=86400, show_spinner=False)
    def get_movie_details_extended(self, movie_id: int) -> Movie:
        """Get complete movie details with credits and similar movies"""
        data = self._make_request(
            f"movie/{movie_id}",
            {"append_to_response": "credits,similar"}
        )
        return self._parse_movie_result(data, full_details=True)

    @st.cache_data(ttl=3600)
    def get_movie_videos(self, movie_id: int) -> List[Video]:
        """Get available videos for a movie"""
        data = self._make_request(f"movie/{movie_id}/videos")
        return [
            Video(key=v["key"], type=v["type"], site=v["site"])
            for v in data.get("results", [])
            if v["site"] == "YouTube" and v["type"] == "Trailer"
        ]

# Singleton instance
try:
    tmdb_client = TMDBClient()
except Exception as e:
    import sys
    print(f"Failed to initialize TMDB client: {str(e)}", file=sys.stderr)
    tmdb_client = None