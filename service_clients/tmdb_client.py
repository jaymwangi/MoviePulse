"""
TMDB API Client with Complete Performance Instrumentation
--------------------------------------------------------
A fully-featured TMDB API client with:
- Comprehensive performance monitoring
- Multi-layer caching
- Advanced error handling
- Full type hints
- Detailed logging
- Streamlit integration
"""

import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple, Union, Any
import requests
from tenacity import retry, wait_exponential, stop_after_attempt,retry_if_exception_type
from diskcache import Cache as DiskCache
from cachetools import TTLCache
import streamlit as st

from logging.handlers import RotatingFileHandler

# Constants
PERF_LOG_PREFIX = "[PERF]"
CACHE_DIR = "tmdb_cache"
LOG_FILE = "logs/tmdb_client.log"
MAX_LOG_SIZE = 5_000_000  # 5 MB
LOG_BACKUP_COUNT = 5
DEFAULT_TIMEOUT = 10
MEMORY_CACHE_SIZE = 1000
MEMORY_CACHE_TTL = 3600  # 1 hour

# Data model classes
class Genre:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class Person:
    def __init__(self, id: int, name: str, role: str, profile_path: Optional[str] = None, 
                 known_for_department: Optional[str] = None):
        self.id = id
        self.name = name
        self.role = role
        self.profile_path = profile_path
        self.known_for_department = known_for_department

class Video:
    def __init__(self, key: str, type: str, site: str):
        self.key = key
        self.type = type
        self.site = site

class Movie:
    def __init__(self, id: int, title: str, overview: str, release_date: str,
                 poster_path: Optional[str], backdrop_path: Optional[str],
                 vote_average: float, runtime: Optional[int] = None,
                 genres: Optional[List[Genre]] = None, directors: Optional[List[Person]] = None,
                 cast: Optional[List[Person]] = None, similar_movies: Optional[List[int]] = None,
                 videos: Optional[List[Video]] = None):
        self.id = id
        self.title = title
        self.overview = overview
        self.release_date = release_date
        self.poster_path = poster_path
        self.backdrop_path = backdrop_path
        self.vote_average = vote_average
        self.runtime = runtime
        self.genres = genres or []
        self.directors = directors or []
        self.cast = cast or []
        self.similar_movies = similar_movies or []
        self.videos = videos or []

def configure_logging():
    """Set up consistent structured logging with rotating file handler."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S"
    ))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False

    return logger

logger = configure_logging()


class FallbackStrategy(Enum):
    """Strategies for handling empty search results."""
    NONE = auto()
    RELAX_ALL = auto()
    RELAX_GRADUAL = auto()
    RELAX_RATING_FIRST = auto()
    RELAX_GENRE_FIRST = auto()

class TMDBClient:
    """Main TMDB API client class with full instrumentation."""
    
    def __init__(self):
        """Initialize client with proper attributes"""
        init_start = time.perf_counter()
        logger.info("Starting TMDBClient initialization")
        
        try:
            # Initialize essential attributes first
            self.default_timeout = DEFAULT_TIMEOUT  # Make sure this constant is defined
            self.memory_cache = TTLCache(maxsize=MEMORY_CACHE_SIZE, ttl=MEMORY_CACHE_TTL)
            self.disk_cache = DiskCache(CACHE_DIR)
            
            # API Key Acquisition
            self.api_key = self._get_api_key()
            if not self.api_key:
                raise RuntimeError("TMDB_API_KEY not found in any location")
            
            # Determine API version
            self.api_version = 4 if self.api_key.startswith("eyJ") else 3
            
            # Session Setup
            self.base_url = "https://api.themoviedb.org/3"
            self.session = requests.Session()
            
            if self.api_version == 4:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json;charset=utf-8"
                })
            else:
                self.session.params = {"api_key": self.api_key}
                
            # Test connection
            if not self._test_connection():
                raise RuntimeError("Initial connection test failed")
                
            logger.info(f"{PERF_LOG_PREFIX} Client initialized in {time.perf_counter()-init_start:.4f}s")
        except Exception as e:
            logger.critical(f"Initialization failed: {str(e)}")
            raise

    def _get_api_key(self) -> str:
        """Hierarchical API key lookup with precise timing."""
        lookup_start = time.perf_counter()
        try:
            sources = [
                ("Streamlit secrets", lambda: st.secrets.get("TMDB_API_KEY") if hasattr(st, "secrets") else None),
                ("Environment variable", lambda: os.getenv("TMDB_API_KEY")),
            ]
            
            for source_name, get_key in sources:
                try:
                    if api_key := get_key():
                        logger.info(f"Found API key in {source_name}")
                        return api_key
                except Exception as e:
                    logger.debug(f"Failed to check {source_name}: {str(e)}")

            # Check .env files
            for level in range(4):
                env_path = Path(__file__).parents[level] / ".env"
                if env_path.exists():
                    try:
                        from dotenv import load_dotenv
                        load_dotenv(env_path)
                        if api_key := os.getenv("TMDB_API_KEY"):
                            logger.info(f"Found API key in .env at {env_path}")
                            return api_key
                    except Exception as e:
                        logger.debug(f"Failed to load .env at {env_path}: {str(e)}")

            raise RuntimeError("TMDB_API_KEY not found in any location. Please set the API key.")
        finally:
            elapsed = time.perf_counter() - lookup_start
            logger.debug(f"{PERF_LOG_PREFIX} API key lookup took {elapsed:.6f}s")


    def _test_connection(self):
        """Test API connectivity with simple request"""
        try:
            test_start = time.perf_counter()
            response = self.session.get(f"{self.base_url}/configuration", timeout=5)
            response.raise_for_status()
            logger.info(f"Connection test succeeded in {time.perf_counter()-test_start:.2f}s")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Dict:
        """Execute API request with proper timeout handling"""
        try:
            # Version-specific request handling
            if self.api_version == 4:
                response = self.session.get(
                    f"{self.base_url}/{endpoint}",
                    params=params,
                    timeout=self.default_timeout
                )
            else:
                # For v3, params already include api_key
                response = self.session.get(
                    f"{self.base_url}/{endpoint}",
                    params=params,
                    timeout=self.default_timeout
                )
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def search_movies(
        self,
        query: str,
        filters: Optional[Dict] = None,
        fallback_strategy: FallbackStrategy = FallbackStrategy.RELAX_GRADUAL,
        page: int = 1
    ) -> Tuple[List[Movie], int]:
        """Search movies with complete performance breakdown."""
        search_start = time.perf_counter()
        logger.info(f"Starting search for '{query}' with filters: {filters}")
        
        try:
            # Filter Processing
            filter_start = time.perf_counter()
            validated_filters = self._validate_filters(filters) if filters else None
            params = self._build_search_params(query, validated_filters, page)
            filter_duration = time.perf_counter() - filter_start

            # API Request
            api_start = time.perf_counter()
            with st.spinner(f"Searching '{query}'..."):
                data = self._make_request("search/movie", params)
            api_duration = time.perf_counter() - api_start

            # Result Processing
            processing_start = time.perf_counter()
            if not data.get("results"):
                if validated_filters and fallback_strategy != FallbackStrategy.NONE:
                    result = self._handle_empty_results(
                        query, params, validated_filters, fallback_strategy, page
                    )
                else:
                    result = [], 0
            else:
                movies = [self._parse_movie_result(m) for m in data["results"]]
                result = movies, data.get("total_pages", 1)
            processing_duration = time.perf_counter() - processing_start

            total_duration = time.perf_counter() - search_start
            logger.info(
                f"{PERF_LOG_PREFIX} Search completed in {total_duration:.4f}s | "
                f"Filters: {filter_duration:.4f}s | "
                f"API: {api_duration:.4f}s | "
                f"Processing: {processing_duration:.4f}s | "
                f"Results: {len(result[0])} movies"
            )
            return result
            
        except Exception as e:
            elapsed = time.perf_counter() - search_start
            logger.error(f"{PERF_LOG_PREFIX} Search failed after {elapsed:.4f}s: {str(e)}")
            st.error(f"Search failed: {str(e)}")
            return [], 0
        
    def get_popular_people(self, limit: int = 200) -> List[Person]:
        """Get list of popular actors/actresses with instrumentation"""
        logger.info(f"Fetching top {limit} popular people")
        fetch_start = time.perf_counter()
        
        try:
            people = []
            page = 1
            
            while len(people) < limit:
                api_start = time.perf_counter()
                data = self._make_request(
                    "person/popular",
                    {"page": page, "language": "en-US"}
                )
                api_duration = time.perf_counter() - api_start
                
                # Filter for actors only and process results
                parse_start = time.perf_counter()
                batch = [
                    Person(
                        id=p["id"],
                        name=p["name"],
                        role="Actor",
                        profile_path=p.get("profile_path"),
                        known_for_department=p.get("known_for_department", "Acting")
                    )
                    for p in data.get("results", [])
                    if p.get("known_for_department") == "Acting"
                ]
                people.extend(batch)
                parse_duration = time.perf_counter() - parse_start
                
                logger.debug(
                    f"{PERF_LOG_PREFIX} Page {page} processed | "
                    f"API: {api_duration:.3f}s | "
                    f"Parse: {parse_duration:.3f}s | "
                    f"Total: {len(people)}/{limit}"
                )
                
                page += 1
                if page > data.get("total_pages", 1):
                    break
            
            elapsed = time.perf_counter() - fetch_start
            logger.info(
                f"{PERF_LOG_PREFIX} Retrieved {len(people)} people in {elapsed:.2f}s"
            )
            return people[:limit]
            
        except Exception as e:
            elapsed = time.perf_counter() - fetch_start
            logger.error(
                f"{PERF_LOG_PREFIX} Failed to fetch popular people after {elapsed:.2f}s: {str(e)}"
            )
            raise
        
    def get_person_filmography(self, person_id: int) -> List[Movie]:
        """Get complete filmography for a person with instrumentation"""
        logger.info(f"Fetching filmography for person {person_id}")
        fetch_start = time.perf_counter()
        
        try:
            # Get both movie credits and TV credits
            api_start = time.perf_counter()
            data = self._make_request(
                f"person/{person_id}/combined_credits",
                {"language": "en-US"}
            )
            api_duration = time.perf_counter() - api_start
            
            # Process both movie and TV appearances
            processing_start = time.perf_counter()
            filmography = []
            
            # Process movie appearances
            for credit in data.get("cast", []):
                if credit.get("media_type") == "movie" and credit.get("id"):
                    filmography.append(
                        Movie(
                            id=credit["id"],
                            title=credit.get("title", "Untitled"),
                            overview=credit.get("overview", ""),
                            release_date=credit.get("release_date", ""),
                            poster_path=credit.get("poster_path"),
                            backdrop_path=credit.get("backdrop_path"),
                            vote_average=credit.get("vote_average", 0),
                            genres=[],  # Will be filled if full details are fetched
                            cast=[]     # Will be filled if full details are fetched
                        )
                    )
            
            processing_duration = time.perf_counter() - processing_start
            elapsed = time.perf_counter() - fetch_start
            logger.info(
                f"{PERF_LOG_PREFIX} Retrieved {len(filmography)} credits in {elapsed:.2f}s | "
                f"API: {api_duration:.3f}s | "
                f"Processing: {processing_duration:.3f}s"
            )
            return filmography
            
        except Exception as e:
            elapsed = time.perf_counter() - fetch_start
            logger.error(
                f"{PERF_LOG_PREFIX} Failed to fetch filmography after {elapsed:.2f}s: {str(e)}"
            )
            raise

    def get_person_details(self, person_id: int) -> Person:
        """Get detailed information about a person with instrumentation"""
        logger.info(f"Fetching details for person {person_id}")
        fetch_start = time.perf_counter()
        
        try:
            api_start = time.perf_counter()
            data = self._make_request(
                f"person/{person_id}",
                {"append_to_response": "combined_credits,external_ids"}
            )
            api_duration = time.perf_counter() - api_start
            
            processing_start = time.perf_counter()
            person = Person(
                id=data["id"],
                name=data.get("name", "Unknown"),
                role="Actor",  # Default role
                profile_path=data.get("profile_path"),
                known_for_department=data.get("known_for_department", "Acting")
            )
            processing_duration = time.perf_counter() - processing_start
            
            elapsed = time.perf_counter() - fetch_start
            logger.info(
                f"{PERF_LOG_PREFIX} Retrieved person details in {elapsed:.2f}s | "
                f"API: {api_duration:.3f}s | "
                f"Processing: {processing_duration:.3f}s"
            )
            return person
            
        except Exception as e:
            elapsed = time.perf_counter() - fetch_start
            logger.error(
                f"{PERF_LOG_PREFIX} Failed to fetch person details after {elapsed:.2f}s: {str(e)}"
            )
            raise

    def get_movie_details(self, movie_id: int) -> Movie:
        """Get movie details with detailed timing metrics."""
        details_start = time.perf_counter()
        logger.info(f"Fetching details for movie ID: {movie_id}")
        
        try:
            # API Request
            api_start = time.perf_counter()
            data = self._make_request(
                f"movie/{movie_id}",
                {"append_to_response": "credits,similar,videos"}
            )
            api_duration = time.perf_counter() - api_start

            # Data Parsing
            parse_start = time.perf_counter()
            movie = self._parse_movie_result(data, full_details=True)
            parse_duration = time.perf_counter() - parse_start

            total_duration = time.perf_counter() - details_start
            logger.info(
                f"{PERF_LOG_PREFIX} Details fetched in {total_duration:.4f}s | "
                f"API: {api_duration:.4f}s | "
                f"Parsing: {parse_duration:.4f}s"
            )
            return movie
            
        except Exception as e:
            elapsed = time.perf_counter() - details_start
            logger.error(f"{PERF_LOG_PREFIX} Failed to fetch details after {elapsed:.4f}s: {str(e)}")
            st.error(f"Failed to load movie details: {str(e)}")
            raise

    def get_genres(self) -> List[Genre]:
        """Get genre list with proper timeout handling"""
        try:
            data = self._make_request("genre/movie/list")
            return [Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])]
        except Exception as e:
            logger.error(f"Failed to fetch genres: {str(e)}")
            return []
        
    def get_trending_movies(self, time_window: str = "week", page: int = 1) -> Tuple[List[Movie], int]:
        """Get trending movies with comprehensive performance tracking and error handling.
        
        Args:
            time_window: Either "day" or "week" for trending period
            page: Page number of results to fetch
            
        Returns:
            Tuple of (movies_list, total_pages)
            
        Raises:
            ValueError: If invalid time_window is provided
        """
        trending_start = time.perf_counter()
        logger.info(f"Fetching trending movies for {time_window} (page {page})")
        
        # Validate input parameters first
        if time_window not in ["day", "week"]:
            error_msg = f"Invalid time_window: {time_window}. Must be 'day' or 'week'"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # API Request with timing
            api_start = time.perf_counter()
            data = self._make_request(
                f"trending/movie/{time_window}",
                {"page": page, "language": "en-US"}  # Added language parameter
            )
            api_duration = time.perf_counter() - api_start

            # Data Parsing with timing
            parse_start = time.perf_counter()
            movies = []
            for movie_data in data.get("results", []):
                try:
                    movies.append(self._parse_movie_result(movie_data))
                except Exception as parse_error:
                    logger.warning(f"Failed to parse movie {movie_data.get('id')}: {str(parse_error)}")
                    continue
                    
            total_pages = min(data.get("total_pages", 1), 500)  # TMDB API limits to 500 pages
            parse_duration = time.perf_counter() - parse_start

            # Log performance metrics
            total_duration = time.perf_counter() - trending_start
            logger.info(
                f"{PERF_LOG_PREFIX} Trending movies fetched | "
                f"Count: {len(movies)} | "
                f"Total: {total_duration:.3f}s | "
                f"API: {api_duration:.3f}s | "
                f"Parse: {parse_duration:.3f}s"
            )
            
            return movies, total_pages
            
        except requests.exceptions.HTTPError as http_err:
            elapsed = time.perf_counter() - trending_start
            logger.error(
                f"{PERF_LOG_PREFIX} HTTP error fetching trending movies | "
                f"Status: {http_err.response.status_code} | "
                f"Time: {elapsed:.3f}s | "
                f"Error: {str(http_err)}"
            )
            if http_err.response.status_code == 401:
                st.error("Authentication failed - please check your TMDB API key")
            return [], 0
            
        except Exception as e:
            elapsed = time.perf_counter() - trending_start
            logger.error(
                f"{PERF_LOG_PREFIX} Unexpected error fetching trending movies | "
                f"Time: {elapsed:.3f}s | "
                f"Error: {str(e)}"
            )
            st.error(f"Failed to load trending movies: {str(e)}")
            return [], 0

    def _validate_filters(self, filters: Dict) -> Dict:
        """Validate filter parameters with timing."""
        validate_start = time.perf_counter()
        logger.debug(f"Validating filters: {filters}")
        validated = {}
        current_year = datetime.now().year
        
        try:
            if "year_range" in filters:
                try:
                    start, end = filters["year_range"]
                    validated["year_range"] = (
                        max(1900, min(start, current_year)),
                        min(current_year + 5, max(end, start))
                    )
                except (TypeError, ValueError):
                    logger.warning("Invalid year range format")
                    
            if "min_rating" in filters:
                try:
                    validated["min_rating"] = max(0.0, min(10.0, float(filters["min_rating"])))
                except (TypeError, ValueError):
                    logger.warning("Invalid rating value")

            if "genres" in filters:
                validated["genres"] = filters["genres"]
                
            return validated
        finally:
            elapsed = time.perf_counter() - validate_start
            logger.debug(f"{PERF_LOG_PREFIX} Filter validation took {elapsed:.6f}s")

    
    def _get_poster_url(self, poster_path: Optional[str], size: str = 'w500') -> Optional[str]:
        """Generate full poster URL from path."""
        if not poster_path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{poster_path}"

    def _build_search_params(
        self,
        query: str,
        filters: Optional[Dict],
        page: int
    ) -> Dict:
        """Build search parameters with timing."""
        params_start = time.perf_counter()
        try:
            params = {
                "query": query,
                "page": page,
                "include_adult": "false",
                "language": "en-US"
            }
            
            if not filters:
                return params
                
            if filters.get("genres"):
                if genre_ids := self._get_genre_ids_by_names(filters["genres"]):
                    params["with_genres"] = ",".join(map(str, genre_ids))
            
            if filters.get("year_range"):
                start, end = filters["year_range"]
                params.update({
                    "primary_release_date.gte": f"{start}-01-01",
                    "primary_release_date.lte": f"{end}-12-31"
                })
            
            if filters.get("min_rating"):
                params["vote_average.gte"] = filters["min_rating"]
                
            return params
        finally:
            elapsed = time.perf_counter() - params_start
            logger.debug(f"{PERF_LOG_PREFIX} Parameter building took {elapsed:.6f}s")

    def _handle_empty_results(
        self,
        query: str,
        original_params: Dict,
        original_filters: Dict,
        strategy: FallbackStrategy,
        page: int
    ) -> Tuple[List[Movie], int]:
        """Handle empty results with fallback strategy and timing."""
        fallback_start = time.perf_counter()
        logger.info(f"Executing fallback strategy: {strategy.name}")
        
        try:
            if strategy == FallbackStrategy.RELAX_ALL:
                return self._relax_all_filters(query, page)
                
            return self._gradual_relaxation(
                query=query,
                original_params=original_params,
                original_filters=original_filters,
                strategy=strategy,
                page=page
            )
        finally:
            elapsed = time.perf_counter() - fallback_start
            logger.info(f"{PERF_LOG_PREFIX} Fallback handling took {elapsed:.4f}s")

    def _relax_all_filters(self, query: str, page: int) -> Tuple[List[Movie], int]:
        """Remove all filters and retry search with timing."""
        relax_start = time.perf_counter()
        try:
            params = {
                "query": query,
                "page": page,
                "include_adult": "false",
                "language": "en-US"
            }
            
            data = self._make_request("search/movie", params)
            st.warning("No results with filters - showing unfiltered results")
            return [self._parse_movie_result(m) for m in data.get("results", [])], data.get("total_pages", 1)
        finally:
            elapsed = time.perf_counter() - relax_start
            logger.debug(f"{PERF_LOG_PREFIX} Full relaxation took {elapsed:.4f}s")

    def _gradual_relaxation(
        self,
        query: str,
        original_params: Dict,
        original_filters: Dict,
        strategy: FallbackStrategy,
        page: int
    ) -> Tuple[List[Movie], int]:
        """Gradually relax filters with timing."""
        gradual_start = time.perf_counter()
        try:
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
        finally:
            elapsed = time.perf_counter() - gradual_start
            logger.debug(f"{PERF_LOG_PREFIX} Gradual relaxation took {elapsed:.4f}s")

    def _get_relaxation_steps(self, strategy: FallbackStrategy) -> List[Dict]:
        """Get relaxation steps with timing."""
        steps_start = time.perf_counter()
        try:
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
        finally:
            elapsed = time.perf_counter() - steps_start
            logger.debug(f"{PERF_LOG_PREFIX} Step generation took {elapsed:.6f}s")

    def _parse_movie_result(self, data: Dict, full_details: bool = False) -> Movie:
        """Parse movie result with precise timing."""
        parse_start = time.perf_counter()
        try:
            movie = Movie(
                id=data.get("id", 0),
                title=data.get("title", "Untitled"),
                overview=data.get("overview", ""),
                release_date=data.get("release_date", ""),
                poster_path=data.get("poster_path"),
                backdrop_path=data.get("backdrop_path"),
                vote_average=data.get("vote_average", 0),
                runtime=data.get("runtime", 0) if full_details else None,
                genres=[Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])],
                directors=[
                    Person(
                        id=p["id"],
                        name=p["name"],
                        role="Director",
                        known_for_department=p.get("known_for_department", "Directing")
                    )
                    for p in data.get("credits", {}).get("crew", [])
                    if p.get("job") == "Director"
                ] if full_details else [],
                cast=[
                    Person(
                        id=p["id"],
                        name=p["name"],
                        role=p.get("character", "Actor"),
                        profile_path=p.get("profile_path"),
                        known_for_department=p.get("known_for_department", "Acting")
                    )
                    for p in data.get("credits", {}).get("cast", [])[:10]
                ] if full_details else [],
                similar_movies=[
                    m["id"] for m in data.get("similar", {}).get("results", [])[:5]
                ] if full_details else [],
                videos=[
                    Video(key=v["key"], type=v["type"], site=v["site"])
                    for v in data.get("videos", {}).get("results", [])
                    if v["site"] == "YouTube" and v["type"] == "Trailer"
                ] if full_details else []
            )
            
            elapsed = time.perf_counter() - parse_start
            logger.debug(f"{PERF_LOG_PREFIX} Parsed movie in {elapsed:.6f}s")
            return movie
        except Exception as e:
            elapsed = time.perf_counter() - parse_start
            logger.error(f"{PERF_LOG_PREFIX} Failed to parse movie after {elapsed:.6f}s: {str(e)}")
            raise

    def _get_genre_ids_by_names(self, genre_names: List[str]) -> List[int]:
        """Convert genre names to IDs with timing."""
        genre_start = time.perf_counter()
        try:
            all_genres = self.get_genres()
            name_to_id = {g.name.lower(): g.id for g in all_genres}
            
            ids = []
            for name in genre_names:
                lower_name = name.lower()
                if lower_name in name_to_id:
                    ids.append(name_to_id[lower_name])
                else:
                    logger.warning(f"Ignoring unknown genre: {name}")
                    st.warning(f"Ignoring unknown genre: {name}")
            
            return ids
        finally:
            elapsed = time.perf_counter() - genre_start
            logger.debug(f"{PERF_LOG_PREFIX} Genre ID lookup took {elapsed:.6f}s")

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def get_popular_movies(self, limit: int = 10, page: int = 1) -> List[Movie]:
    """Get popular movies with full instrumentation.
    
    Args:
        limit: Maximum number of movies to return
        page: Page number of results to fetch
        
    Returns:
        List of Movie objects
        
    Raises:
        RequestException: If API request fails after retries
    """
    fetch_start = time.perf_counter()
    logger.info(f"Fetching {limit} popular movies from page {page}")
    
    try:
        # API Request
        api_start = time.perf_counter()
        url = f"{self.base_url}/movie/popular"
        params = {
            "api_key": self.api_key,
            "language": "en-US",
            "page": page
        }
        response = self._make_request(url, params)
        api_duration = time.perf_counter() - api_start
        
        # Data Processing
        process_start = time.perf_counter()
        movies = [self._parse_movie_result(m) for m in response.get("results", [])[:limit]]
        process_duration = time.perf_counter() - process_start
        
        elapsed = time.perf_counter() - fetch_start
        logger.info(
            f"{PERF_LOG_PREFIX} Retrieved {len(movies)} popular movies in {elapsed:.2f}s | "
            f"API: {api_duration:.3f}s | "
            f"Processing: {process_duration:.3f}s"
        )
        
        return movies
        
    except Exception as e:
        elapsed = time.perf_counter() - fetch_start
        logger.error(
            f"{PERF_LOG_PREFIX} Failed to fetch popular movies after {elapsed:.2f}s: {str(e)}"
        )
        raise

# Singleton pattern with full instrumentation
try:
    logger.info("Initializing TMDBClient singleton")
    init_start = time.perf_counter()
    tmdb_client = TMDBClient()
    elapsed = time.perf_counter() - init_start
    logger.info(f"{PERF_LOG_PREFIX} Singleton initialized in {elapsed:.4f}s")
except Exception as e:
    import sys
    logger.critical(f"TMDB client initialization failed: {str(e)}")
    print(f"Failed to initialize TMDB client: {str(e)}", file=sys.stderr)
    tmdb_client = None
    if 'streamlit' in sys.modules:
        st.error("TMDB client unavailable - some features disabled")