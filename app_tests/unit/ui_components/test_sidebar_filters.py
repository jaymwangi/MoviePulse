import streamlit as st
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json
import logging
from ui_components.SidebarFilters import (
    load_genres,
    _init_session_state,
    _validate_current_state,
    _sync_state_to_url,
    _should_trigger_search,
    reset_filters,
    get_active_filters,
    DEFAULT_YEAR_RANGE,
    DEFAULT_RATING_RANGE,
    DEFAULT_POPULARITY_RANGE
)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Fixtures
@pytest.fixture
def mock_genres_file(tmp_path):
    genres = [
        {"id": 28, "name": "Action"},
        {"id": 12, "name": "Adventure"},
        {"id": 16, "name": "Animation"}
    ]
    file = tmp_path / "genres.json"
    file.write_text(json.dumps(genres))
    logger.debug(f"Created mock genres file at {file}")
    return str(file)

@pytest.fixture
def mock_session_state():
    state = {
        "selected_genres": ["Action", "Adventure"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "last_filter_change": datetime.now().timestamp(),
        "filter_init_complete": True
    }
    logger.debug(f"Created mock session state: {state}")
    return state

# Tests
def test_load_genres_success(mock_genres_file):
    logger.debug("Testing load_genres success with mock file")
    with patch("ui_components.SidebarFilters.GENRES_FILE", mock_genres_file):
        result = load_genres()
    logger.debug(f"Loaded genres: {result}")
    assert len(result) == 3
    assert result[0]["name"] == "Action"
    logger.debug("test_load_genres_success passed")

def test_load_genres_file_not_found():
    logger.debug("Testing load_genres fallback on file not found")
    with patch("ui_components.SidebarFilters.GENRES_FILE", "nonexistent.json"):
        result = load_genres()
    logger.debug(f"Fallback genres loaded: {result}")
    assert isinstance(result, list)
    assert any(g["name"] == "Action" for g in result)
    logger.debug("test_load_genres_file_not_found passed")

def test_load_genres_invalid_json(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid}")
    logger.debug(f"Testing load_genres fallback on invalid JSON file {invalid_file}")
    with patch("ui_components.SidebarFilters.GENRES_FILE", str(invalid_file)):
        result = load_genres()
    logger.debug(f"Fallback genres loaded: {result}")
    assert isinstance(result, list)
    assert any(g["name"] == "Action" for g in result)
    logger.debug("test_load_genres_invalid_json passed")

def test_init_session_state_empty():
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = {}
    logger.debug("Testing _init_session_state with empty URL params")
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    logger.debug(f"Session state after init: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == []
    assert st.session_state["year_range"] == DEFAULT_YEAR_RANGE
    assert st.session_state["rating_range"] == DEFAULT_RATING_RANGE
    assert st.session_state["popularity_range"] == DEFAULT_POPULARITY_RANGE
    assert st.session_state["filter_init_complete"] is True
    logger.debug("test_init_session_state_empty passed")

def test_init_session_state_from_url_params():
    url_params = {
        "genres": "Action,Adventure",  # string, so .split() works
        "year_min": "2010",
        "year_max": "2020",
        "rating_min": "7.0",
        "rating_max": "9.0",
        "popularity_min": "30",
        "popularity_max": "70"
    }
    logger.debug(f"Testing _init_session_state with URL params: {url_params}")
    st.session_state.clear()
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = url_params
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    logger.debug(f"Session state after init: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == ["Action", "Adventure"]
    assert st.session_state["year_range"] == (2010, 2020)
    assert st.session_state["rating_range"] == (7.0, 9.0)
    assert st.session_state["popularity_range"] == (30, 70)
    logger.debug("test_init_session_state_from_url_params passed")



def test_validate_current_state(mock_session_state):
    logger.debug(f"Testing _validate_current_state with mock state: {mock_session_state}")
    st.session_state.update(mock_session_state)
    _validate_current_state()
    # Test invalid values
    st.session_state.update({
        "selected_genres": ["InvalidGenre"],
        "year_range": (1800, 2050),
        "rating_range": (-1.0, 11.0),
        "popularity_range": (-10, 110)
    })
    _validate_current_state()
    logger.debug(f"Session state after validation: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == []
    assert st.session_state["year_range"][0] >= 1950
    assert st.session_state["year_range"][1] <= datetime.now().year
    assert 0.0 <= st.session_state["rating_range"][0] <= 10.0
    assert 0.0 <= st.session_state["rating_range"][1] <= 10.0
    assert 0 <= st.session_state["popularity_range"][0] <= 100
    assert 0 <= st.session_state["popularity_range"][1] <= 100
    logger.debug("test_validate_current_state passed")

def test_sync_state_to_url(mock_session_state):
    st.session_state.update(mock_session_state)
    mock_query_params = MagicMock()
    logger.debug("Testing _sync_state_to_url")
    with patch("streamlit.query_params", mock_query_params):
        _sync_state_to_url()
    logger.debug(f"Expected call args: genres='Action,Adventure', year_min='2010', etc.")
    mock_query_params.update.assert_called_once_with(
        genres="Action,Adventure",
        year_min="2010",
        year_max="2020",
        rating_min="7.0",
        rating_max="9.0",
        popularity_min="30",
        popularity_max="70"
    )
    logger.debug("test_sync_state_to_url passed")

def test_should_trigger_search():
    logger.debug("Testing _should_trigger_search behavior")
    if "last_filter_change" in st.session_state:
        del st.session_state["last_filter_change"]
    assert _should_trigger_search() is True
    
    st.session_state["last_filter_change"] = datetime.now().timestamp()
    assert _should_trigger_search() is False
    
    st.session_state["last_filter_change"] = datetime.now().timestamp() - 1.0
    assert _should_trigger_search() is True
    logger.debug("test_should_trigger_search passed")

def test_reset_filters():
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "last_filter_change": datetime.now().timestamp()
    })
    mock_toast = MagicMock()
    logger.debug("Testing reset_filters")
    with patch("streamlit.toast", mock_toast):
        reset_filters()
    logger.debug(f"Session state after reset: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == []
    assert st.session_state["year_range"] == DEFAULT_YEAR_RANGE
    assert st.session_state["rating_range"] == DEFAULT_RATING_RANGE
    assert st.session_state["popularity_range"] == DEFAULT_POPULARITY_RANGE
    mock_toast.assert_called_once_with("Filters reset to defaults", icon="♻️")
    logger.debug("test_reset_filters passed")

def test_get_active_filters(mock_session_state):
    st.session_state.update(mock_session_state)
    logger.debug("Testing get_active_filters with recent last_filter_change (ready should be False)")
    result = get_active_filters()
    logger.debug(f"Active filters: {result}")
    assert result == {
        "genres": ["Action", "Adventure"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "ready": False
    }
    logger.debug("test_get_active_filters passed")

def test_get_active_filters_ready_for_search():
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "last_filter_change": datetime.now().timestamp() - 1.0
    })
    logger.debug("Testing get_active_filters with old last_filter_change (ready should be True)")
    result = get_active_filters()
    logger.debug(f"Active filters: {result}")
    assert result["ready"] is True
    logger.debug("test_get_active_filters_ready_for_search passed")
