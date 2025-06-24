"""
TMDB API Client for MoviePulse
-----------------------------
Author: Glitajay
Credit: The Movie Database (TMDB) API (https://www.themoviedb.org/documentation/api)
"""

import os
from pathlib import Path
import requests
from typing import Optional, List, Dict
from tenacity import retry, wait_exponential, stop_after_attempt
from core_config.constants import Movie, Person, Genre
import streamlit as st

class TMDBClient:
    def __init__(self):
        """Initialize with API key from .env or Streamlit secrets."""
        self.api_key = self._get_api_key()
        if not self.api_key:
            raise RuntimeError("TMDB_API_KEY not found in .env or Streamlit secrets.")
        
        self.base_url = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _get_api_key(self) -> Optional[str]:
        """Try to retrieve API key from environment or Streamlit secrets."""
        from dotenv import load_dotenv

        # Walk up to 3 levels from current file to find .env
        for level in range(1, 4):
            env_path = Path(__file__).resolve().parents[level] / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                api_key = os.getenv("TMDB_API_KEY")
                if api_key:
                    return api_key

        # Fallback to Streamlit secrets
        try:
            import streamlit as st
            return st.secrets.get("TMDB_API_KEY")
        except Exception:
            return None

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10),
           stop=stop_after_attempt(3))
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Dict:
        """Core request handler with retry logic."""
        params = params or {}
        params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"TMDB API request failed ({endpoint}): {str(e)}")

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def search_movies(_self, query: str, year: Optional[int] = None) -> List[Movie]:
        """
        Search for movies by title with Streamlit integration.
        
        Args:
            query: Search query string
            year: Optional release year filter
            
        Returns:
            List of Movie objects or empty list if no results
            
        Raises:
            RuntimeError: If API request fails
        """
        params = {"query": query, "include_adult": "false"}
        if year:
            params["year"] = year

        try:
            with st.spinner(f"Searching for '{query}'..."):
                data = _self._make_request("search/movie", params)
                
            if not data.get("results"):
                st.warning(f"No movies found for '{query}'")
                return []
                
            return [_self._parse_movie_result(m) for m in data.get("results", [])]
            
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            raise

    @st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
    def get_movie_details(_self, movie_id: int) -> Movie:
        """Fetch full movie details with credits."""
        try:
            with st.spinner("Loading movie details..."):
                data = _self._make_request(
                    f"movie/{movie_id}",
                    {"append_to_response": "credits"}
                )
            return _self._parse_movie_result(data, full_details=True)
        except Exception as e:
            st.error(f"Failed to load movie details: {str(e)}")
            raise

    @st.cache_data(ttl=86400 * 7)  # Cache for 1 week
    def get_genres(_self) -> List[Genre]:
        """Fetch all available movie genres."""
        try:
            data = _self._make_request("genre/movie/list")
            return [Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])]
        except Exception as e:
            st.error(f"Failed to load genres: {str(e)}")
            return []

    def _parse_movie_result(self, data: Dict, full_details: bool = False) -> Movie:
        """Convert TMDB JSON to Movie object with safe null handling."""
        return Movie(
            id=data.get("id", 0),
            title=data.get("title", "Untitled"),
            overview=data.get("overview", ""),
            release_date=data.get("release_date", ""),
            poster_path=data.get("poster_path", ""),
            genres=[Genre(id=g["id"], name=g["name"]) for g in data.get("genres", [])],
            directors=[
                Person(id=p["id"], name=p["name"], role="director")
                for p in data.get("credits", {}).get("crew", [])
                if p.get("job") == "Director"
            ] if full_details else [],
            cast=[
                Person(id=p["id"], name=p["name"], role="actor", profile_path=p.get("profile_path"))
                for p in data.get("credits", {}).get("cast", [])[:10]
            ] if full_details else []
        )

# Singleton instance
try:
    tmdb_client = TMDBClient()
except Exception as e:
    import sys
    print(f"TMDB client initialization failed: {str(e)}", file=sys.stderr)
    tmdb_client = None