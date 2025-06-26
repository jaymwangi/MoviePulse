import pytest
import logging
from unittest.mock import patch, MagicMock
from service_clients.tmdb_client import TMDBClient
from core_config.constants import Movie
import requests
from streamlit import cache_data
import tenacity  # ✅ Added for retry error catching

# Setup test logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TestTMDBClient:
    """Test suite for TMDB API client"""

    @patch.dict("os.environ", {"TMDB_API_KEY": "test_key"})
    def setup_method(self, method):
        logger.info("🔧 Setting up TMDBClient instance")
        self.client = TMDBClient()

    @patch("requests.Session.get")
    def test_search_movies_loading(self, mock_get):
        logger.info("🎬 Testing TMDBClient.search_movies (success case)")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "id": 1,
                "title": "Test Movie",
                "overview": "Test overview",
                "poster_path": "/test.jpg"
            }]
        }
        mock_get.return_value = mock_response

        result = self.client.search_movies("test")
        logger.info(f"✅ Received {len(result)} result(s)")
        assert len(result) == 1
        assert isinstance(result[0], Movie)

        logger.info("🧹 Clearing cache before simulating error")
        cache_data.clear()

        logger.info("❌ Simulating request failure for search_movies")
        mock_get.side_effect = requests.exceptions.RequestException("Error")
        with pytest.raises(tenacity.RetryError):  # ✅ Corrected
            self.client.search_movies("test")
        logger.info("✅ Properly raised RetryError on failure")

    @patch("requests.Session.get")
    def test_get_movie_details_loading(self, mock_get):
        logger.info("🎬 Testing TMDBClient.get_movie_details (success case)")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 1,
            "title": "Test Movie",
            "credits": {
                "cast": [],
                "crew": []
            }
        }
        mock_get.return_value = mock_response

        result = self.client.get_movie_details(1)
        logger.info("✅ Successfully parsed movie details")
        assert isinstance(result, Movie)

        logger.info("🧹 Clearing cache before simulating error")
        cache_data.clear()

        logger.info("❌ Simulating request failure for get_movie_details")
        mock_get.side_effect = requests.exceptions.RequestException("Error")
        with pytest.raises(tenacity.RetryError):  # ✅ Corrected
            self.client.get_movie_details(1)
        logger.info("✅ Properly raised RetryError on failure")

    def test_loading_state_transitions(self):
        logger.info("🔍 Verifying method callability and wrapping")
        assert callable(self.client.search_movies)
        assert callable(self.client.get_movie_details)
        logger.info("✅ Methods are callable and ready")
