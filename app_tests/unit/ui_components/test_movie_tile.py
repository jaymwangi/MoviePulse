import pytest
import logging
from unittest.mock import patch
from app_ui.components.MovieTile import MovieTile

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class TestMovieTile:
    @pytest.fixture
    def sample_movie(self):
        return {
            "poster_path": "valid_path.jpg",
            "title": "Test Movie",
            "release_year": "2023"
        }

    @patch("streamlit.markdown")
    def test_hover_animations(self, mock_markdown, sample_movie):
        logger.info("🎬 Testing hover animations")
        MovieTile(sample_movie)

        css_blocks = [call.args[0] for call in mock_markdown.call_args_list]
        for css in css_blocks:
            logger.info(f"🔍 CSS block:\n{css}")

        assert any("transition: transform 0.2s" in css for css in css_blocks)
        assert any(".movie-tile:hover" in css for css in css_blocks)
        assert any("transform: scale(1.05)" in css for css in css_blocks)
        logger.info("✅ Hover animation CSS validated")

    @patch("streamlit.image")
    def test_fallback_image_handling(self, mock_image):
        logger.info("🧪 Testing fallback image logic")
        MovieTile({"title": "No Poster Movie", "poster_path": None})
        image_paths = [call.args[0] for call in mock_image.call_args_list]
        for path in image_paths:
            logger.info(f"📷 Image used: {path}")
        assert any("image-fallback.svg" in path for path in image_paths)
        logger.info("✅ Fallback image used correctly")

    @patch("streamlit.markdown")
    def test_loading_states(self, mock_markdown):
        logger.info("⌛ Testing loading state rendering")
        MovieTile({"title": "Loading..."})
        calls = [str(call.args) for call in mock_markdown.call_args_list]
        for c in calls:
            logger.info(f"🆔 markdown call args: {c}")
        assert any("movie-tile" in c for c in calls)
        logger.info("✅ Loading state rendering confirmed")

    @patch("streamlit.markdown")
    @patch("streamlit.write")
    def test_testid_generation(self, mock_write, mock_markdown, sample_movie):
        logger.info("🔎 Testing testid suffix generation")
        MovieTile(sample_movie, testid_suffix="123")

        all_calls = [str(call.args) for call in mock_write.call_args_list + mock_markdown.call_args_list]
        for c in all_calls:
            logger.info(f"🆔 Rendered call args: {c}")

        assert any("movie-tile-123" in c for c in all_calls)
        assert any("movie-title-123" in c for c in all_calls)
        logger.info("✅ Test ID suffixes validated")
