# app_tests/integration/test_search_flow.py
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from streamlit_pages.page_02_Search import render_search_page, display_search_results, show_empty_state
from ui_components.MovieTile import MovieTile
from ui_components.MovieGridView import MovieGridView
from session_utils.state_tracker import init_session_state, get_active_filters


@pytest.fixture
def mock_tmdb_client():
    """Fixture to mock TMDBClient with sample responses"""
    logger.info("🔧 Patching TMDBClient.search_movies with mock response")
    with patch('service_clients.tmdb_client.TMDBClient') as mock:
        client = mock.return_value
        client.search_movies.return_value = [
            {
                "id": 123,
                "title": "Test Movie",
                "poster_path": "test_path.jpg",
                "release_year": "2023",
                "overview": "Test overview"
            }
        ]
        yield client


@pytest.fixture
def mock_streamlit():
    """Fixture to mock Streamlit display functions"""
    logger.info("🔧 Patching core Streamlit UI components")
    with patch.object(st, "container"), \
         patch.object(st, "columns"), \
         patch.object(st, "image"), \
         patch.object(st, "markdown"), \
         patch.object(st, "subheader"), \
         patch.object(st, "expander"), \
         patch.object(st, "caption"):
        yield


def test_init_session_state():
    """Test that session state initializes correctly"""
    logger.info("🧪 Testing session state initialization")
    init_session_state()
    assert 'filters' in st.session_state
    assert 'genres' in st.session_state['filters']
    assert st.session_state['filters']['year_range'] == (2000, 2024)
    logger.info("✅ Session state initialized with correct filters")


def test_show_empty_state(mock_streamlit):
    """Test the empty state rendering"""
    logger.info("🧪 Testing empty search state display")
    show_empty_state()
    assert st.markdown.call_count > 0
    st.expander.assert_called_with("💡 Search Tips", expanded=True)
    logger.info("✅ Empty state rendered with tips")


def test_display_search_results(mock_streamlit):
    """Test search results display logic"""
    st.session_state["global_search_query"] = "test query"
    logger.info(f"🧪 Testing results display for query: {st.session_state['global_search_query']}")
    display_search_results()
    st.subheader.assert_called_with("Results for: 'test query'", divider="red")
    assert st.image.call_count == 8
    logger.info("✅ Displayed 8 placeholder results")


def test_search_flow_with_query(mock_streamlit, mock_tmdb_client):
    """Full flow: query in session state → show results"""
    st.session_state["global_search_query"] = "test"
    logger.info("🧪 Testing full search flow (query exists)")
    with patch("streamlit_pages.page_02_Search.load_custom_css"):
        render_search_page()
        st.container.assert_called()
        mock_tmdb_client.search_movies.assert_not_called()
        logger.info("✅ render_search_page() responded correctly to session query")


def test_search_flow_without_query(mock_streamlit):
    """Flow without query should fallback to empty state"""
    logger.info("🧪 Testing search flow without query")
    if "global_search_query" in st.session_state:
        del st.session_state["global_search_query"]

    with patch("streamlit_pages.page_02_Search.load_custom_css"), \
         patch("streamlit_pages.page_02_Search.show_empty_state") as mock_empty:
        render_search_page()
        mock_empty.assert_called_once()
        logger.info("✅ Empty state rendered correctly when no query")


def test_movie_tile_component(mock_streamlit):
    """Test MovieTile component logic"""
    logger.info("🧪 Testing MovieTile rendering")
    test_movie = {
        "title": "Test Movie",
        "poster_path": "test_path.jpg",
        "release_year": "2023"
    }

    with patch("os.path.exists", return_value=True):
        MovieTile(test_movie)
        st.image.assert_called_with("test_path.jpg", use_container_width=True, output_format="PNG")
        st.markdown.assert_any_call(
            '<div class="movie-title" data-testid="movie-title">Test Movie</div>',
            unsafe_allow_html=True
        )
    logger.info("✅ MovieTile rendered title, year, and image successfully")


def test_movie_grid_view(mock_streamlit):
    """Test MovieGridView layout logic"""
    logger.info("🧪 Testing MovieGridView component with 2 mock movies")
    test_movies = [
        {"title": "Movie 1", "poster_path": "path1.jpg"},
        {"title": "Movie 2", "poster_path": "path2.jpg"}
    ]

    with patch("ui_components.MovieTile.MovieTile") as mock_tile:
        MovieGridView(test_movies)
        assert mock_tile.call_count == 2
        logger.info("✅ MovieGridView rendered correct number of tiles")


def test_active_filters():
    """Test the get_active_filters method"""
    logger.info("🧪 Testing get_active_filters logic")
    init_session_state()
    filters = get_active_filters()
    assert "genres" in filters
    assert filters["year_range"] == (2000, 2024)
    logger.info("✅ Active filters fetched successfully")
