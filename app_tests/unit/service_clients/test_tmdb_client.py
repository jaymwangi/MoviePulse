# app_tests/unit/service_clients/test_tmdb_client.py

import pytest
import logging
import json
from unittest.mock import patch, MagicMock, mock_open
from service_clients.tmdb_client import (
    TMDBClient,
    FallbackStrategy,
    Person,
    Movie,
    Genre
)
import requests
from typing import List

# Setup test logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TestTMDBClient:
    """Comprehensive test suite for TMDBClient with hybrid filtering"""

    @patch.dict("os.environ", {"TMDB_API_KEY": "test_key"})
    @patch.object(TMDBClient, '_test_connection', return_value=True)
    def setup_method(self, method, mock_connection):
        logger.info("🔧 Setting up TMDBClient instance")
        
        # Mock the API key retrieval
        with patch.object(TMDBClient, '_get_api_key', return_value="test_key"):
            self.client = TMDBClient()
            # For v3 API, api_key is stored in session params
            self.client.session.params = {"api_key": "test_key"}
        
        # Sample data for tests
        self.sample_movie_data = {
            "id": 1,
            "title": "Test Movie",
            "overview": "Test overview",
            "poster_path": "/test.jpg",
            "backdrop_path": "/backdrop.jpg",
            "release_date": "2020-01-01",
            "vote_average": 8.5,
            "genres": [{"id": 28, "name": "Action"}],
            "credits": {
                "cast": [{"id": 1, "name": "Actor 1", "character": "Hero", "profile_path": "/actor1.jpg"}],
                "crew": [{"id": 2, "name": "Director 1", "job": "Director"}]
            }
        }
        
        self.sample_actor_data = {
            "id": 123,
            "name": "Test Actor",
            "biography": "Test bio",
            "birthday": "1980-01-01",
            "deathday": None,
            "place_of_birth": "Test City",
            "profile_path": "/test_actor.jpg",
            "known_for_department": "Acting"
        }
        
        self.sample_director_data = {
            "id": 456,
            "name": "Test Director",
            "biography": "Director bio",
            "birthday": "1970-01-01",
            "deathday": None,
            "place_of_birth": "Director City",
            "profile_path": "/test_director.jpg",
            "known_for_department": "Directing"
        }
        
        self.sample_filmography_data = {
            "cast": [
                {
                    "id": 1,
                    "title": "Movie 1",
                    "character": "Lead Role",
                    "release_date": "2020-01-01",
                    "poster_path": "/movie1.jpg",
                    "backdrop_path": "/backdrop1.jpg",
                    "vote_average": 8.0,
                    "media_type": "movie"
                }
            ],
            "crew": [
                {
                    "id": 2,
                    "title": "Directed Movie",
                    "job": "Director",
                    "department": "Directing",
                    "release_date": "2019-01-01",
                    "poster_path": "/directed.jpg",
                    "backdrop_path": "/backdrop2.jpg",
                    "vote_average": 8.5,
                    "media_type": "movie"
                }
            ]
        }
        
        self.sample_local_actor_data = {
            "actors": [
                {
                    "id": 123,
                    "name": "Local Actor",
                    "profile_path": "/local_actor.jpg",
                    "known_for_department": "Acting",
                    "filmography": [
                        {
                            "id": 100,
                            "title": "Local Movie",
                            "year": 2020,
                            "poster_path": "/local_movie.jpg",
                            "backdrop_path": "/local_backdrop.jpg"
                        }
                    ]
                }
            ]
        }

    @patch("requests.Session.get")
    def test_search_movies_basic(self, mock_get):
        """Test basic movie search functionality"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [self.sample_movie_data], 
            "total_pages": 1
        }
        mock_get.return_value = mock_response

        with patch.object(self.client, '_parse_movie_result', return_value=Movie(
            id=1, title="Test Movie", overview="Test overview",
            poster_path="/test.jpg", backdrop_path="/backdrop.jpg",
            release_date="2020-01-01", vote_average=8.5, genres=[]
        )):
            movies, total_pages = self.client.search_movies("test")
            assert len(movies) == 1
            assert isinstance(movies[0], Movie)
            assert total_pages == 1

    @patch("requests.Session.get")
    def test_search_movies_with_filters(self, mock_get):
        """Test movie search with filters"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [self.sample_movie_data], "total_pages": 1
        }
        mock_get.return_value = mock_response

        with patch.object(self.client, 'get_genres', return_value=[Genre(id=28, name="Action")]):
            movies, _ = self.client.search_movies("test", filters={
                "genres": ["Action"],
                "year_range": (2015, 2022),
                "min_rating": 8.0
            })

        called_params = mock_get.call_args[1]["params"]
        assert "with_genres" in called_params
        assert "vote_average.gte" in called_params
        assert "primary_release_date.gte" in called_params

    @patch("requests.Session.get")
    def test_fallback_strategies(self, mock_get):
        """Test fallback strategies when no results found"""
        empty_response = MagicMock()
        empty_response.status_code = 200
        empty_response.raise_for_status = MagicMock()
        empty_response.json.return_value = {"results": [], "total_pages": 0}

        fallback_response = MagicMock()
        fallback_response.status_code = 200
        fallback_response.raise_for_status = MagicMock()
        fallback_response.json.return_value = {"results": [self.sample_movie_data], "total_pages": 1}

        mock_get.side_effect = [empty_response, fallback_response]

        with patch.object(self.client, 'get_genres', return_value=[Genre(id=28, name="Action")]), \
            patch.object(self.client, '_parse_movie_result', return_value=Movie(
                id=1, title="Test Movie", overview="Test overview",
                poster_path="/test.jpg", backdrop_path="/backdrop.jpg",
                release_date="2020-01-01", vote_average=8.5, genres=[]
            )):
            movies, _ = self.client.search_movies(
                "test",
                filters={"genres": ["Action"], "min_rating": 9.0},
                fallback_strategy=FallbackStrategy.RELAX_ALL
            )
            assert len(movies) == 1

    @patch("streamlit.cache_data", side_effect=lambda *a, **kw: (lambda f: f))
    @patch("requests.Session.get")
    def test_error_handling(self, mock_get, mock_cache):
        """Test error handling during API calls"""
        mock_get.side_effect = requests.exceptions.RequestException("API Failure")

        movies, total_pages = self.client.search_movies("test")

        assert movies == []
        assert total_pages == 0
        assert mock_get.call_count >= 3

    @patch("requests.Session.get")
    def test_get_trending_movies(self, mock_get):
        """Test fetching trending movies"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": [self.sample_movie_data]}
        mock_get.return_value = mock_response

        with patch.object(self.client, '_parse_movie_result', return_value=Movie(
            id=1, title="Test Movie", overview="Test overview",
            poster_path="/test.jpg", backdrop_path="/backdrop.jpg",
            release_date="2020-01-01", vote_average=8.5, genres=[]
        )):
            movies, _ = self.client.get_trending_movies()
            assert len(movies) == 1
            assert isinstance(movies[0], Movie)

    @patch("requests.Session.get")
    def test_get_movie_details(self, mock_get):
        """Test fetching movie details"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.sample_movie_data
        mock_get.return_value = mock_response

        with patch.object(self.client, "_parse_movie_result", return_value=Movie(
            id=1, title="Test Movie", overview="Test", release_date="2020-01-01",
            poster_path="/test.jpg", backdrop_path="/backdrop.jpg",
            vote_average=8.5, genres=[]
        )):
            movie = self.client.get_movie_details(1)
            assert isinstance(movie, Movie)

    @patch("requests.Session.get")
    def test_genre_handling(self, mock_get):
        """Test genre handling functionality"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "genres": [{"id": 28, "name": "Action"}]
        }
        mock_get.return_value = mock_response

        genres = self.client.get_genres()
        assert genres[0].name == "Action"
        ids = self.client._get_genre_ids_by_names(["Action"])
        assert ids == [28]
        unknown = self.client._get_genre_ids_by_names(["Unknown"])
        assert unknown == []

    def test_parameter_validation(self):
        """Test parameter validation"""
        with pytest.raises(ValueError):
            self.client.get_trending_movies(time_window="invalid")

    def test_singleton_behavior(self):
        """Test singleton behavior"""
        from service_clients.tmdb_client import tmdb_client
        assert isinstance(tmdb_client, TMDBClient)

    @patch("requests.Session.get")
    def test_get_actor_details_api_success(self, mock_get):
        """Test successful API call for actor details"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_actor_data
        mock_get.return_value = mock_response

        actor = self.client.get_person_details(123)
        
        assert isinstance(actor, Person)
        assert actor.id == 123
        assert actor.name == "Test Actor"
        assert actor.known_for_department == "Acting"
        assert actor.profile_path == "/test_actor.jpg"
        
        mock_get.assert_called_once_with(
            "https://api.themoviedb.org/3/person/123",
            params={
                "append_to_response": "combined_credits,external_ids"
            },
            timeout=10
        )

    @patch("requests.Session.get")
    def test_get_actor_details_api_failure_fallback(self, mock_get):
        """Test fallback to local data when API fails"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        json_data = json.dumps(self.sample_local_actor_data)
        
        with patch("builtins.open", mock_open(read_data=json_data)):
            actor = self.client.get_person_details(123)
            
            assert isinstance(actor, Person)
            assert actor.id == 123
            assert actor.name == "Local Actor"
            assert actor.profile_path == "/local_actor.jpg"

    def test_get_actor_details_no_data(self):
        """Test when no actor data is available"""
        with patch("requests.Session.get", side_effect=requests.exceptions.RequestException("API Error")), \
             patch("builtins.open", mock_open(read_data=json.dumps({"actors": []}))):
            
            actor = self.client.get_person_details(999)
            assert actor is None

    @patch("requests.Session.get")
    def test_get_director_details_api_success(self, mock_get):
        """Test successful API call for director details"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_director_data
        mock_get.return_value = mock_response

        director = self.client.get_director_details(456)
        
        assert director["id"] == 456
        assert director["name"] == "Test Director"
        assert director["biography"] == "Director bio"
        assert director["profile_path"] == "/test_director.jpg"
        
        mock_get.assert_called_once_with(
            "https://api.themoviedb.org/3/person/456",
            params={
                "append_to_response": "external_ids,images"
            },
            timeout=10
        )

    @patch("requests.Session.get")
    def test_get_director_filmography_api_success(self, mock_get):
        """Test successful API call for director filmography"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_filmography_data
        mock_get.return_value = mock_response

        filmography = self.client.get_director_filmography(456)
        
        assert len(filmography) == 1
        assert filmography[0]["title"] == "Directed Movie"
        assert filmography[0]["crew_role"] == "Director"
        
        mock_get.assert_called_once_with(
            "https://api.themoviedb.org/3/person/456/combined_credits",
            params={
                "language": "en-US"
            },
            timeout=10
        )

    @patch("requests.Session.get")
    def test_get_director_filmography_empty_results(self, mock_get):
        """Test empty results from director filmography"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"cast": [], "crew": []}
        mock_get.return_value = mock_response

        filmography = self.client.get_director_filmography(456)
        assert len(filmography) == 0

    @patch("requests.Session.get")
    def test_get_person_filmography_api_success(self, mock_get):
        """Test successful API call for person filmography"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cast": [
                {
                    "id": 1,
                    "title": "Movie 1",
                    "character": "Lead Role",
                    "release_date": "2020-01-01",
                    "poster_path": "/movie1.jpg",
                    "backdrop_path": "/backdrop1.jpg",
                    "vote_average": 8.0,
                    "media_type": "movie"
                },
                {
                    "id": 2,
                    "title": "Movie 2",
                    "character": "Supporting Role",
                    "release_date": "2021-01-01",
                    "poster_path": "/movie2.jpg",
                    "backdrop_path": "/backdrop2.jpg",
                    "vote_average": 7.5,
                    "media_type": "movie"
                }
            ],
            "crew": [
                {
                    "id": 3,
                    "title": "Directed Movie",
                    "job": "Director",
                    "department": "Directing",
                    "release_date": "2019-01-01",
                    "poster_path": "/directed.jpg",
                    "backdrop_path": "/backdrop3.jpg",
                    "vote_average": 8.5,
                    "media_type": "movie"
                }
            ]
        }
        mock_get.return_value = mock_response

        filmography = self.client.get_person_filmography(123)
        
        # Implementation only returns cast entries, not crew
        assert len(filmography) == 2
        assert isinstance(filmography[0], Movie)
        assert filmography[0].title == "Movie 1"
        assert isinstance(filmography[1], Movie)
        assert filmography[1].title == "Movie 2"

    @patch("requests.Session.get")
    def test_get_person_filmography_api_failure_fallback(self, mock_get):
        """Test fallback to local data when API fails"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        json_data = json.dumps(self.sample_local_actor_data)
        
        with patch("builtins.open", mock_open(read_data=json_data)):
            filmography = self.client.get_person_filmography(123)
            
            assert len(filmography) == 1
            assert isinstance(filmography[0], Movie)
            assert filmography[0].title == "Local Movie"
            assert filmography[0].release_date == "2020-01-01"

    def test_get_person_filmography_no_data(self):
        """Test when no filmography data is available"""
        with patch("requests.Session.get", side_effect=requests.exceptions.RequestException("API Error")), \
             patch("builtins.open", mock_open(read_data=json.dumps({"actors": []}))):
            
            filmography = self.client.get_person_filmography(999)
            assert len(filmography) == 0

    @patch("requests.Session.get")
    def test_get_popular_people(self, mock_get):
        """Test fetching popular people"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 1,
                    "name": "Actor 1",
                    "known_for_department": "Acting",
                    "profile_path": "/actor1.jpg"
                },
                {
                    "id": 2,
                    "name": "Crew 1",
                    "known_for_department": "Production",
                    "profile_path": "/crew1.jpg"
                }
            ],
            "total_pages": 1
        }
        mock_get.return_value = mock_response

        people = self.client.get_popular_people(limit=1)
        assert len(people) == 1
        assert people[0].name == "Actor 1"
        assert people[0].known_for_department == "Acting"

    def get_popular_movies(self, limit: int = 10, page: int = 1) -> List[Movie]:
            """Get popular movies from TMDB API"""
            try:
                data = self._make_request(
                    "movie/popular",
                    {"page": page, "language": "en-US"}
                )
                return [
                    self._parse_movie_result(m) 
                    for m in data.get("results", [])[:limit]
                ]
            except Exception as e:
                logger.error(f"Failed to fetch popular movies: {str(e)}")
                return []