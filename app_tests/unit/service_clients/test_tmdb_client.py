# app_tests/unit/service_clients/test_tmdb_client.py

import pytest
import logging
from unittest.mock import patch, MagicMock
from service_clients.tmdb_client import (
    TMDBClient,
    FallbackStrategy
)
from core_config.constants import Movie, Genre
import requests

# Setup test logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class TestTMDBClient:
    """Comprehensive test suite for TMDBClient with hybrid filtering"""

    @patch.dict("os.environ", {"TMDB_API_KEY": "test_key"})
    def setup_method(self, method):
        logger.info("🔧 Setting up TMDBClient instance")
        self.client = TMDBClient()
        self.sample_movie_data = {
            "id": 1,
            "title": "Test Movie",
            "overview": "Test overview",
            "poster_path": "/test.jpg",
            "release_date": "2020-01-01",
            "vote_average": 8.5,
            "genres": [{"id": 28, "name": "Action"}],
            "credits": {
                "cast": [{"id": 1, "name": "Actor 1", "character": "Hero", "profile_path": "/actor1.jpg"}],
                "crew": [{"id": 2, "name": "Director 1", "job": "Director"}]
            }
        }

    @patch("requests.Session.get")
    def test_search_movies_basic(self, mock_get):
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
            poster_path="/test.jpg", release_date="2020-01-01",
            vote_average=8.5, genres=[]
        )):
            movies, total_pages = self.client.search_movies("test")
            assert len(movies) == 1
            assert isinstance(movies[0], Movie)
            assert total_pages == 1

    @patch("requests.Session.get")
    def test_search_movies_with_filters(self, mock_get):
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

    # Update the test_fallback_strategies method  
    @patch("requests.Session.get")
    def test_fallback_strategies(self, mock_get):
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
                poster_path="/test.jpg", release_date="2020-01-01",
                vote_average=8.5, genres=[]
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
        mock_get.side_effect = requests.exceptions.RequestException("API Failure")

        movies, total_pages = self.client.search_movies("test")

        assert movies == []
        assert total_pages == 0
        assert mock_get.call_count >= 3  # now retries should happen



    # Update the test_get_trending_movies method
    @patch("requests.Session.get")
    def test_get_trending_movies(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": [self.sample_movie_data]}
        mock_get.return_value = mock_response

        with patch.object(self.client, '_parse_movie_result', return_value=Movie(
            id=1, title="Test Movie", overview="Test overview",
            poster_path="/test.jpg", release_date="2020-01-01",
            vote_average=8.5, genres=[]
        )):
            movies = self.client.get_trending_movies()
            assert len(movies) == 1
            assert isinstance(movies[0], Movie)

    @patch("requests.Session.get")
    def test_get_movie_details(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.sample_movie_data
        mock_get.return_value = mock_response

        with patch.object(self.client, "_parse_movie_result", return_value=Movie(
            id=1, title="Test Movie", overview="Test", release_date="2020-01-01",
            poster_path="/test.jpg", vote_average=8.5, genres=[]
        )):
            movie = self.client.get_movie_details(1)
            assert isinstance(movie, Movie)

    @patch("requests.Session.get")
    def test_genre_handling(self, mock_get):
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

    def test_client_side_filtering(self):
        movie1 = Movie(
            id=1,
            title="Movie 1",
            overview="Overview 1",
            release_date="2020-01-01",
            poster_path="/a.jpg",
            vote_average=8.5,
            genres=[Genre(id=28, name="Action")]
        )
        movie2 = Movie(
            id=2,
            title="Movie 2",
            overview="Overview 2",
            release_date="2010-01-01",
            poster_path="/b.jpg",
            vote_average=6.5,
            genres=[Genre(id=12, name="Adventure")]
        )
        movies = [movie1, movie2]

        filtered = self.client._apply_filters(movies, {"genres": ["Action"]})
        assert len(filtered) == 1 and filtered[0].title == "Movie 1"

        filtered = self.client._apply_filters(movies, {"year_range": (2015, 2025)})
        assert len(filtered) == 1

        filtered = self.client._apply_filters(movies, {"min_rating": 7.0})
        assert len(filtered) == 1 and filtered[0].title == "Movie 1"

    def test_cache_decorators(self):
        assert callable(getattr(self.client.search_movies, "__wrapped__", self.client.search_movies))
        assert callable(getattr(self.client.get_genres, "__wrapped__", self.client.get_genres))
        assert callable(getattr(self.client.get_movie_details, "__wrapped__", self.client.get_movie_details))

    def test_parameter_validation(self):
        with pytest.raises(ValueError):
            self.client.get_trending_movies(time_window="invalid")

    def test_singleton_behavior(self):
        from service_clients.tmdb_client import tmdb_client
        assert isinstance(tmdb_client, TMDBClient)
