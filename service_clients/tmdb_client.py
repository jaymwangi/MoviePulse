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
                 videos: Optional[List[Video]] = None, vote_count: int = 0):
        self.id = id
        self.title = title
        self.overview = overview
        self.release_date = release_date
        self.poster_path = poster_path
        self.backdrop_path = backdrop_path
        self.vote_average = vote_average
        self.vote_count = vote_count  # Add this
        self.runtime = runtime
        self.genres = genres or []
        self.directors = directors or []
        self.cast = cast or []
        self.similar_movies = similar_movies or []
        self.videos = videos or []
        self.popularity = 0.0  # Initialize popularity

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
        page: int = 1,
        critic_mode: str = "balanced"
    ) -> Tuple[List[Movie], int]:
        """Search movies with complete data for MovieTile and critic mode filtering."""
        search_start = time.perf_counter()
        logger.info(f"Starting search for '{query}' with filters: {filters}, critic mode: {critic_mode}")
        
        try:
            # Build search params
            params = self._build_search_params(query, filters, page)
            
            # API Request
            api_start = time.perf_counter()
            with st.spinner(f"Searching '{query}'..."):
                search_data = self._make_request("search/movie", params)
            api_duration = time.perf_counter() - api_start

            # Process results with complete data
            processing_start = time.perf_counter()
            if not search_data.get("results"):
                if filters and fallback_strategy != FallbackStrategy.NONE:
                    result = self._handle_empty_results(query, params, filters, fallback_strategy, page)
                else:
                    result = [], 0
            else:
                movies = []
                for m in search_data["results"]:
                    try:
                        # Get full details for each movie to ensure complete data
                        movie_id = m["id"]
                        movie_data = self._make_request(f"movie/{movie_id}", {
                            "append_to_response": "credits",
                            "language": "en-US"
                        })
                        parsed_movie = self._parse_movie_result(movie_data)
                        movies.append(parsed_movie)
                    except Exception as e:
                        logger.warning(f"Failed to get full details for movie {m.get('id')}: {str(e)}")
                        # Fallback to basic data if full details fail
                        parsed_movie = self._parse_movie_result(m)
                        movies.append(parsed_movie)
                
                # Apply critic mode filtering
                if critic_mode != "balanced":
                    movies = self._apply_critic_mode(movies, critic_mode)
                    
                result = movies, search_data.get("total_pages", 1)
                
            processing_duration = time.perf_counter() - processing_start

            total_duration = time.perf_counter() - search_start
            logger.info(
                f"{PERF_LOG_PREFIX} Search completed in {total_duration:.4f}s | "
                f"API: {api_duration:.4f}s | "
                f"Processing: {processing_duration:.4f}s | "
                f"Results: {len(result[0])} movies | "
                f"Critic Mode: {critic_mode}"
            )
            return result
            
        except Exception as e:
            elapsed = time.perf_counter() - search_start
            logger.error(f"{PERF_LOG_PREFIX} Search failed after {elapsed:.4f}s: {str(e)}")
            st.error(f"Search failed: {str(e)}")
            return [], 0

    def _apply_critic_mode(self, movies: List[Movie], critic_mode: str) -> List[Movie]:
        """Apply critic mode filtering to movie results.
        
        Args:
            movies: List of Movie objects to filter
            critic_mode: One of "balanced", "arthouse", "blockbuster", "indie"
            
        Returns:
            Filtered and sorted list of Movie objects
        """
        if critic_mode == "balanced" or not movies:
            return movies  # No filtering for balanced mode
        
        logger.info(f"Applying critic mode filtering: {critic_mode} to {len(movies)} movies")
        filter_start = time.perf_counter()
        
        try:
            if critic_mode == "arthouse":
                # Filter for arthouse films (high rating, low popularity, certain genres)
                filtered_movies = [
                    m for m in movies 
                    if m.vote_average >= 7.0  # High rating
                    and getattr(m, 'popularity', 0) < 50.0  # Lower popularity
                ]
                # Sort by rating (descending), then popularity (ascending)
                filtered_movies.sort(key=lambda x: (
                    -x.vote_average,  # High rating first
                    getattr(x, 'popularity', 0)  # Lower popularity first
                ))
                
            elif critic_mode == "blockbuster":
                # Filter for blockbuster films (high popularity, certain genres)
                filtered_movies = [
                    m for m in movies 
                    if getattr(m, 'popularity', 0) > 100.0  # High popularity
                    and m.vote_count > 1000  # Many votes (FIXED: was 'x.vote_count')
                ]
                # Sort by popularity (descending), then vote count (descending)
                filtered_movies.sort(key=lambda x: (
                    -getattr(x, 'popularity', 0),  # High popularity first
                    -x.vote_count  # Many votes first
                ))
                
            elif critic_mode == "indie":
                # Filter for indie films (good rating, moderate popularity, certain genres)
                filtered_movies = [
                    m for m in movies 
                    if m.vote_average >= 6.5  # Good rating
                    and 20.0 < getattr(m, 'popularity', 0) < 80.0  # Moderate popularity
                ]
                # Sort by rating (descending), then popularity (ascending)
                filtered_movies.sort(key=lambda x: (
                    -x.vote_average,  # Good rating first
                    getattr(x, 'popularity', 0)  # Moderate popularity
                ))
                
            else:
                logger.warning(f"Unknown critic mode: {critic_mode}, using balanced mode")
                return movies
            
            elapsed = time.perf_counter() - filter_start
            logger.info(
                f"{PERF_LOG_PREFIX} Critic mode filtering completed in {elapsed:.3f}s | "
                f"Original: {len(movies)} | Filtered: {len(filtered_movies)}"
            )
            
            return filtered_movies
            
        except Exception as e:
            elapsed = time.perf_counter() - filter_start
            logger.error(f"{PERF_LOG_PREFIX} Critic mode filtering failed after {elapsed:.3f}s: {str(e)}")
            return movies  # Return original list on error

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
        
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_person_filmography(
        self, 
        person_id: int,
        role_type: str = "acting"  # "acting" or "directing"
    ) -> List[Movie]:
        """Get complete filmography for a person with instrumentation and fallback
        
        Args:
            person_id: TMDB person ID
            role_type: Type of roles to fetch ("acting" or "directing")
            
        Returns:
            List of Movie objects
        """
        logger.info(f"Fetching {role_type} filmography for person {person_id}")
        fetch_start = time.perf_counter()
        
        try:
            # First try TMDB API
            try:
                api_start = time.perf_counter()
                data = self._make_request(
                    f"person/{person_id}/combined_credits",
                    {"language": "en-US"}
                )
                api_duration = time.perf_counter() - api_start
                
                # Process based on role type
                processing_start = time.perf_counter()
                filmography = []
                
                if role_type == "directing":
                    # Get directing credits from crew
                    for credit in data.get("crew", []):
                        if (credit.get("media_type") == "movie" and 
                            credit.get("id") and 
                            credit.get("job") == "Director"):
                            filmography.append(
                                Movie(
                                    id=credit["id"],
                                    title=credit.get("title", "Untitled"),
                                    overview=credit.get("overview", ""),
                                    release_date=credit.get("release_date", ""),
                                    poster_path=credit.get("poster_path"),
                                    backdrop_path=credit.get("backdrop_path"),
                                    vote_average=credit.get("vote_average", 0),
                                    genres=[],
                                    cast=[]
                                )
                            )
                else:  # Default to acting roles
                    # Get acting credits from cast
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
                                    genres=[],
                                    cast=[]
                                )
                            )
                
                processing_duration = time.perf_counter() - processing_start
                elapsed = time.perf_counter() - fetch_start
                logger.info(
                    f"{PERF_LOG_PREFIX} Retrieved {len(filmography)} {role_type} credits from API in {elapsed:.2f}s | "
                    f"API: {api_duration:.3f}s | "
                    f"Processing: {processing_duration:.3f}s"
                )
                return filmography
                
            except requests.exceptions.RequestException as api_error:
                logger.warning(f"API request failed, falling back to local data: {str(api_error)}")
                
                # Fallback to local actors.json
                local_start = time.perf_counter()
                filmography = []
                actors_file = Path("static_data/actors.json")
                if actors_file.exists():
                    with open(actors_file, "r") as f:
                        actors_data = json.load(f)
                        for actor in actors_data.get("actors", []):
                            if actor["id"] == person_id:
                                # Check if we should filter for directing roles
                                if role_type == "directing":
                                    # Only include if person is marked as director
                                    if "Directing" not in actor.get("known_for_department", ""):
                                        logger.debug(f"Person {person_id} not marked as director in local data")
                                        return []
                                
                                for movie in actor.get("filmography", []):
                                    filmography.append(
                                        Movie(
                                            id=movie["id"],
                                            title=movie.get("title", "Untitled"),
                                            overview="",  # Not available in local data
                                            release_date=str(movie.get("year", "")) if movie.get("year") else "",
                                            poster_path=movie.get("poster_path"),
                                            backdrop_path=None,
                                            vote_average=0,
                                            genres=[],
                                            cast=[]
                                        )
                                    )
                                
                                elapsed = time.perf_counter() - fetch_start
                                local_duration = time.perf_counter() - local_start
                                logger.info(
                                    f"{PERF_LOG_PREFIX} Retrieved {len(filmography)} {role_type} credits from local file in {elapsed:.2f}s | "
                                    f"Local: {local_duration:.3f}s"
                                )
                                return filmography
                    
                logger.warning(f"Person {person_id} not found in local data")
                return []
                
        except Exception as e:
            elapsed = time.perf_counter() - fetch_start
            logger.error(
                f"{PERF_LOG_PREFIX} Failed to fetch {role_type} filmography after {elapsed:.2f}s: {str(e)}"
            )
            return []

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_person_details(
        self, 
        person_id: int,
        role_type: str = None  # Optional: "actor" or "director" for role-specific handling
    ) -> Optional[Person]:
        """Get detailed information about a person with instrumentation and fallback
        
        Args:
            person_id: TMDB person ID
            role_type: Optional role type ("actor" or "director") for specific handling
            
        Returns:
            Person object or None if not found
        """
        logger.info(f"Fetching details for person {person_id}" + 
                (f" (role: {role_type})" if role_type else ""))
        fetch_start = time.perf_counter()
        
        try:
            # First try TMDB API
            try:
                api_start = time.perf_counter()
                data = self._make_request(
                    f"person/{person_id}",
                    {"append_to_response": "combined_credits,external_ids"}
                )
                api_duration = time.perf_counter() - api_start
                
                processing_start = time.perf_counter()
                
                # Determine primary role
                department = data.get("known_for_department", "Acting")
                primary_role = "Director" if department == "Directing" else "Actor"
                
                # If role_type was specified, verify it matches
                if role_type and role_type.lower() not in primary_role.lower():
                    logger.warning(f"Person {person_id} is primarily a {primary_role}, not a {role_type}")
                    return None
                    
                person = Person(
                    id=data["id"],
                    name=data.get("name", "Unknown"),
                    role=primary_role,
                    profile_path=data.get("profile_path"),
                    known_for_department=department,
                    # Additional fields can be added here as needed
                )
                
                processing_duration = time.perf_counter() - processing_start
                elapsed = time.perf_counter() - fetch_start
                logger.info(
                    f"{PERF_LOG_PREFIX} Retrieved person details from API in {elapsed:.2f}s | "
                    f"API: {api_duration:.3f}s | "
                    f"Processing: {processing_duration:.3f}s"
                )
                return person
                
            except requests.exceptions.RequestException as api_error:
                logger.warning(f"API request failed, falling back to local data: {str(api_error)}")
                
                # Fallback to local actors.json
                local_start = time.perf_counter()
                actors_file = Path("static_data/actors.json")
                if actors_file.exists():
                    with open(actors_file, "r") as f:
                        actors_data = json.load(f)
                        for person_data in actors_data.get("actors", []):
                            if person_data["id"] == person_id:
                                # Check role type if specified
                                if role_type:
                                    known_for = person_data.get("known_for_department", "").lower()
                                    if role_type.lower() == "director" and "directing" not in known_for:
                                        logger.debug(f"Person {person_id} not marked as director in local data")
                                        return None
                                    elif role_type.lower() == "actor" and "acting" not in known_for:
                                        logger.debug(f"Person {person_id} not marked as actor in local data")
                                        return None
                                
                                person = Person(
                                    id=person_data["id"],
                                    name=person_data.get("name", "Unknown"),
                                    role="Director" if "Directing" in person_data.get("known_for_department", "") else "Actor",
                                    profile_path=person_data.get("profile_path"),
                                    known_for_department=person_data.get("known_for_department", "Acting")
                                )
                                
                                elapsed = time.perf_counter() - fetch_start
                                local_duration = time.perf_counter() - local_start
                                logger.info(
                                    f"{PERF_LOG_PREFIX} Retrieved person details from local file in {elapsed:.2f}s | "
                                    f"Local: {local_duration:.3f}s"
                                )
                                return person
                    
                logger.warning(f"Person {person_id} not found in local data")
                return None
                
        except Exception as e:
            elapsed = time.perf_counter() - fetch_start
            logger.error(
                f"{PERF_LOG_PREFIX} Failed to fetch person details after {elapsed:.2f}s: {str(e)}"
            )
            return None

    def get_movie_details(self, movie_id: int, include_extra: bool = True) -> Movie:
        """Get complete movie details with all required metadata."""
        details_start = time.perf_counter()
        logger.info(f"Fetching details for movie ID: {movie_id}")
        
        try:
            # Always include credits to get runtime and genres if missing
            append_to_response = ["credits"]
            if include_extra:
                append_to_response.extend(["similar", "videos"])
            
            # API Request with extended details
            api_start = time.perf_counter()
            data = self._make_request(
                f"movie/{movie_id}",
                {"append_to_response": ",".join(append_to_response), "language": "en-US"}
            )
            api_duration = time.perf_counter() - api_start

            # Data Parsing with complete fallbacks
            parse_start = time.perf_counter()
            movie = self._parse_movie_result(data, full_details=include_extra)
            
            # Fallback to get runtime from credits if missing
            if not movie.runtime and data.get('credits', {}).get('crew'):
                for crew_member in data['credits']['crew']:
                    if crew_member.get('job') == 'Director' and 'movie_details' in crew_member:
                        if 'runtime' in crew_member['movie_details']:
                            movie.runtime = crew_member['movie_details']['runtime']
                            break
            
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
        
    def get_trending_movies(self, time_window: str = "week", page: int = 1, critic_mode: str = "balanced") -> Tuple[List[Movie], int]:
        """Get trending movies with complete data including runtime and critic mode filtering."""
        trending_start = time.perf_counter()
        logger.info(f"Fetching trending movies for {time_window} (page {page}) with critic mode: {critic_mode}")
        
        # Validate input parameters first
        if time_window not in ["day", "week"]:
            error_msg = f"Invalid time_window: {time_window}. Must be 'day' or 'week'"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # API Request for trending movies
            api_start = time.perf_counter()
            data = self._make_request(
                f"trending/movie/{time_window}",
                {"page": page, "language": "en-US"}
            )
            api_duration = time.perf_counter() - api_start

            # Process results with complete data
            processing_start = time.perf_counter()
            movies = []
            for movie_data in data.get("results", []):
                try:
                    # Get full details for each movie to ensure complete data
                    movie_id = movie_data["id"]
                    try:
                        full_data = self._make_request(
                            f"movie/{movie_id}",
                            {"append_to_response": "credits", "language": "en-US"}
                        )
                        parsed_movie = self._parse_movie_result(full_data)
                        movies.append(parsed_movie)
                    except Exception as full_detail_error:
                        logger.warning(f"Couldn't get full details for movie {movie_id}, using basic data: {str(full_detail_error)}")
                        parsed_movie = self._parse_movie_result(movie_data)
                        movies.append(parsed_movie)
                except Exception as e:
                    logger.warning(f"Failed to process trending movie {movie_data.get('id')}: {str(e)}")
                    continue
            
            # Apply critic mode filtering
            if critic_mode != "balanced":
                movies = self._apply_critic_mode(movies, critic_mode)
                    
            total_pages = min(data.get("total_pages", 1), 500)  # TMDB API limits to 500 pages
            processing_duration = time.perf_counter() - processing_start

            # Log performance metrics
            total_duration = time.perf_counter() - trending_start
            logger.info(
                f"{PERF_LOG_PREFIX} Trending movies fetched | "
                f"Count: {len(movies)} | "
                f"Critic Mode: {critic_mode} | "
                f"Total: {total_duration:.3f}s | "
                f"API: {api_duration:.3f}s | "
                f"Processing: {processing_duration:.3f}s"
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
        """Parse movie result with complete data for MovieTile."""
        parse_start = time.perf_counter()
        try:
            # Handle genres - ensure we always have a list of dicts with 'name' key
            genres = []
            if data.get("genres"):
                genres = [{"id": g["id"], "name": g["name"]} for g in data["genres"]]
            elif 'genre_ids' in data:
                # For search results that only have genre IDs
                all_genres = self.get_genres()
                genre_map = {g.id: g.name for g in all_genres}
                genres = [{"id": gid, "name": genre_map.get(gid, "Unknown")} 
                        for gid in data.get("genre_ids", [])]
            
            # Handle runtime with proper fallbacks
            runtime = data.get("runtime", 0)
            if runtime == 0 and 'credits' in data and 'crew' in data['credits']:
                for crew_member in data['credits']['crew']:
                    if crew_member.get('job') == 'Director' and 'movie_details' in crew_member:
                        runtime = crew_member['movie_details'].get('runtime', 0)
                        if runtime > 0:
                            break
            
            # Handle release date for upcoming movies
            release_date = data.get("release_date", "")
            if not release_date and data.get("status") == "Upcoming":
                release_date = "Coming Soon"
            
            movie = Movie(
                id=data.get("id", 0),
                title=data.get("title", "Untitled"),
                overview=data.get("overview", "No description available"),
                release_date=release_date,
                poster_path=data.get("poster_path", ""),
                backdrop_path=data.get("backdrop_path", ""),
                vote_average=data.get("vote_average", 0),
                vote_count=data.get("vote_count", 0),  # Add vote_count
                runtime=runtime,
                genres=genres,
                directors=[
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "role": "Director",
                        "profile_path": p.get("profile_path"),
                        "known_for_department": p.get("known_for_department", "Directing")
                    }
                    for p in data.get("credits", {}).get("crew", [])
                    if p.get("job") == "Director"
                ] if full_details else [],
                cast=[
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "role": p.get("character", "Actor"),
                        "profile_path": p.get("profile_path"),
                        "known_for_department": p.get("known_for_department", "Acting")
                    }
                    for p in data.get("credits", {}).get("cast", [])[:10]
                ] if full_details else [],
                similar_movies=[
                    m["id"] for m in data.get("similar", {}).get("results", [])[:5]
                ] if full_details else [],
                videos=[
                    {"key": v["key"], "type": v["type"], "site": v["site"]}
                    for v in data.get("videos", {}).get("results", [])
                    if v["site"] == "YouTube" and v["type"] in ["Trailer", "Teaser"]
                ] if full_details else []
            )
            
            # Add popularity for critic mode filtering
            movie.popularity = data.get("popularity", 0.0)
            
            # Add raw data for debugging
            movie.raw_data = data
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