"""
Test suite for SidebarFilters component.

This module contains unit tests for the SidebarFilters component which handles:
- Loading and validating movie genres
- Initializing and managing filter state
- Synchronizing state with URL parameters
- Filter validation and reset functionality

Tests cover both normal and edge cases for all major functions.
"""

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

# Setup logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fixtures
@pytest.fixture
def mock_genres_file(tmp_path):
    """
    Creates a temporary genres JSON file for testing.
    
    Args:
        tmp_path: pytest temporary directory fixture
        
    Returns:
        str: Path to the temporary genres file
    """
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
    """
    Provides a mock session state with typical filter values.
    
    Returns:
        dict: Dictionary representing a populated session state
    """
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

# Test cases
def test_load_genres_success(mock_genres_file):
    """Tests successful loading of genres from a valid JSON file."""
    logger.debug("Starting test_load_genres_success")
    with patch("ui_components.SidebarFilters.GENRES_FILE", mock_genres_file):
        result = load_genres()
    logger.debug(f"Loaded genres: {result}")
    assert len(result) == 3, "Should load all 3 genres from mock file"
    assert result[0]["name"] == "Action", "First genre should be Action"
    logger.info("test_load_genres_success completed successfully")

def test_load_genres_file_not_found():
    """Tests genre loading fallback when file is not found."""
    logger.debug("Starting test_load_genres_file_not_found")
    with patch("ui_components.SidebarFilters.GENRES_FILE", "nonexistent.json"):
        result = load_genres()
    logger.debug(f"Fallback genres loaded: {result}")
    assert isinstance(result, list), "Should return a list even when file not found"
    assert any(g["name"] == "Action" for g in result), "Fallback should include Action genre"
    logger.info("test_load_genres_file_not_found completed successfully")

def test_load_genres_invalid_json(tmp_path):
    """Tests genre loading fallback when JSON is invalid."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid}")
    logger.debug(f"Testing with invalid JSON file at {invalid_file}")
    with patch("ui_components.SidebarFilters.GENRES_FILE", str(invalid_file)):
        result = load_genres()
    logger.debug(f"Fallback genres loaded: {result}")
    assert isinstance(result, list), "Should return a list even with invalid JSON"
    assert any(g["name"] == "Action" for g in result), "Fallback should include Action genre"
    logger.info("test_load_genres_invalid_json completed successfully")

def test_init_session_state_empty():
    """Tests session state initialization with empty URL parameters."""
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = {}
    logger.debug("Testing empty URL params initialization")
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    logger.debug(f"Initialized session state: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == [], "Genres should be empty"
    assert st.session_state["year_range"] == DEFAULT_YEAR_RANGE, "Should use default year range"
    assert st.session_state["rating_range"] == DEFAULT_RATING_RANGE, "Should use default rating range"
    assert st.session_state["popularity_range"] == DEFAULT_POPULARITY_RANGE, "Should use default popularity range"
    assert st.session_state["filter_init_complete"] is True, "Initialization should be marked complete"
    logger.info("test_init_session_state_empty completed successfully")

def test_init_session_state_from_url_params():
    """Tests session state initialization from populated URL parameters."""
    url_params = {
        "genres": "Action,Adventure",
        "year_min": "2010",
        "year_max": "2020",
        "rating_min": "7.0",
        "rating_max": "9.0",
        "popularity_min": "30",
        "popularity_max": "70"
    }
    logger.debug(f"Initializing with URL params: {url_params}")
    st.session_state.clear()
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = url_params
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    logger.debug(f"Initialized session state: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == ["Action", "Adventure"], "Genres should be parsed correctly"
    assert st.session_state["year_range"] == (2010, 2020), "Year range should be parsed correctly"
    assert st.session_state["rating_range"] == (7.0, 9.0), "Rating range should be parsed correctly"
    assert st.session_state["popularity_range"] == (30, 70), "Popularity range should be parsed correctly"
    logger.info("test_init_session_state_from_url_params completed successfully")

def test_validate_current_state(mock_session_state):
    """Tests validation and correction of invalid filter values."""
    logger.debug(f"Starting validation test with initial state: {mock_session_state}")
    st.session_state.update(mock_session_state)
    _validate_current_state()
    
    # Test with invalid values
    st.session_state.update({
        "selected_genres": ["InvalidGenre"],
        "year_range": (1800, 2050),
        "rating_range": (-1.0, 11.0),
        "popularity_range": (-10, 110)
    })
    _validate_current_state()
    logger.debug(f"State after validation: {dict(st.session_state)}")
    
    assert st.session_state["selected_genres"] == [], "Invalid genres should be cleared"
    assert st.session_state["year_range"][0] >= 1950, "Minimum year should be clamped"
    assert st.session_state["year_range"][1] <= datetime.now().year, "Maximum year should be clamped"
    assert 0.0 <= st.session_state["rating_range"][0] <= 10.0, "Minimum rating should be clamped"
    assert 0.0 <= st.session_state["rating_range"][1] <= 10.0, "Maximum rating should be clamped"
    assert 0 <= st.session_state["popularity_range"][0] <= 100, "Minimum popularity should be clamped"
    assert 0 <= st.session_state["popularity_range"][1] <= 100, "Maximum popularity should be clamped"
    logger.info("test_validate_current_state completed successfully")

def test_sync_state_to_url(mock_session_state):
    """Tests synchronization of session state to URL parameters."""
    st.session_state.update(mock_session_state)
    mock_query_params = MagicMock()
    logger.debug("Testing state to URL synchronization")
    with patch("streamlit.query_params", mock_query_params):
        _sync_state_to_url()
    
    logger.debug("Verifying URL parameter updates")
    mock_query_params.update.assert_called_once_with(
        genres="Action,Adventure",
        year_min="2010",
        year_max="2020",
        rating_min="7.0",
        rating_max="9.0",
        popularity_min="30",
        popularity_max="70"
    )
    logger.info("test_sync_state_to_url completed successfully")

def test_should_trigger_search():
    """Tests search trigger timing logic."""
    logger.debug("Testing search trigger conditions")
    
    # Test when last_filter_change is not set
    if "last_filter_change" in st.session_state:
        del st.session_state["last_filter_change"]
    assert _should_trigger_search() is True, "Should trigger when no timestamp exists"
    
    # Test with recent change
    st.session_state["last_filter_change"] = datetime.now().timestamp()
    assert _should_trigger_search() is False, "Should not trigger immediately after change"
    
    # Test with old change
    st.session_state["last_filter_change"] = datetime.now().timestamp() - 1.0
    assert _should_trigger_search() is True, "Should trigger after delay"
    logger.info("test_should_trigger_search completed successfully")

def test_reset_filters():
    """Tests filter reset functionality."""
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "last_filter_change": datetime.now().timestamp()
    })
    mock_toast = MagicMock()
    logger.debug("Testing filter reset")
    with patch("streamlit.toast", mock_toast):
        reset_filters()
    
    logger.debug(f"State after reset: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == [], "Genres should be cleared"
    assert st.session_state["year_range"] == DEFAULT_YEAR_RANGE, "Year range should be reset"
    assert st.session_state["rating_range"] == DEFAULT_RATING_RANGE, "Rating range should be reset"
    assert st.session_state["popularity_range"] == DEFAULT_POPULARITY_RANGE, "Popularity range should be reset"
    mock_toast.assert_called_once_with("Filters reset to defaults", icon="♻️")
    logger.info("test_reset_filters completed successfully")

def test_get_active_filters(mock_session_state):
    """Tests retrieval of active filters with recent changes."""
    st.session_state.update(mock_session_state)
    logger.debug("Testing get_active_filters with recent changes")
    result = get_active_filters()
    logger.debug(f"Active filters: {result}")
    
    assert result == {
        "genres": ["Action", "Adventure"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "ready": False
    }, "Should return current filters with ready=False for recent changes"
    logger.info("test_get_active_filters completed successfully")

def test_get_active_filters_ready_for_search():
    """Tests filter readiness after change delay."""
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_range": (2010, 2020),
        "rating_range": (7.0, 9.0),
        "popularity_range": (30, 70),
        "last_filter_change": datetime.now().timestamp() - 1.0
    })
    logger.debug("Testing get_active_filters with old changes")
    result = get_active_filters()
    logger.debug(f"Active filters: {result}")
    
    assert result["ready"] is True, "Filters should be ready after delay"
    logger.info("test_get_active_filters_ready_for_search completed successfully")

def test_init_session_state_with_exact_url_params():
    """Tests initialization with exact filter values from URL."""
    url_params = {
        "genres": "Action,Adventure",
        "exact_year": "2015",
        "exact_rating": "8.5",
        "exact_popularity": "50"
    }
    st.session_state.clear()
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = url_params
    logger.debug("Testing initialization with exact URL params")
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    
    logger.debug(f"Initialized state: {dict(st.session_state)}")
    assert st.session_state["year_filter_mode"] == "exact", "Year mode should be exact"
    assert st.session_state["exact_year"] == 2015, "Exact year should be parsed"
    assert st.session_state["rating_filter_mode"] == "exact", "Rating mode should be exact"
    assert st.session_state["exact_rating"] == 8.5, "Exact rating should be parsed"
    assert st.session_state["popularity_filter_mode"] == "exact", "Popularity mode should be exact"
    assert st.session_state["exact_popularity"] == 50, "Exact popularity should be parsed"
    logger.info("test_init_session_state_with_exact_url_params completed successfully")

def test_validate_current_state_with_exact_values():
    """Tests validation of exact filter values."""
    st.session_state.update({
        "year_filter_mode": "exact",
        "exact_year": 1800,
        "rating_filter_mode": "exact",
        "exact_rating": -1.0,
        "popularity_filter_mode": "exact",
        "exact_popularity": -10
    })
    logger.debug("Testing validation of exact values")
    _validate_current_state()
    logger.debug(f"Validated state: {dict(st.session_state)}")
    
    assert st.session_state["exact_year"] == 1950, "Exact year should be clamped"
    assert st.session_state["exact_rating"] == 0.0, "Exact rating should be clamped"
    assert st.session_state["exact_popularity"] == 0, "Exact popularity should be clamped"
    logger.info("test_validate_current_state_with_exact_values completed successfully")

def test_sync_state_to_url_with_exact_values():
    """Tests URL synchronization with exact filter values."""
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_filter_mode": "exact",
        "exact_year": 2015,
        "rating_filter_mode": "exact",
        "exact_rating": 8.5,
        "popularity_filter_mode": "exact",
        "exact_popularity": 50,
        "year_range": DEFAULT_YEAR_RANGE,
        "rating_range": DEFAULT_RATING_RANGE,
        "popularity_range": DEFAULT_POPULARITY_RANGE
    })
    mock_query_params = MagicMock()
    logger.debug("Testing URL sync with exact values")
    with patch("streamlit.query_params", mock_query_params):
        _sync_state_to_url()
    
    logger.debug("Verifying exact parameters in URL update")
    args, kwargs = mock_query_params.update.call_args
    assert kwargs["exact_year"] == "2015", "Exact year should be in URL"
    assert kwargs["exact_rating"] == "8.5", "Exact rating should be in URL"
    assert kwargs["exact_popularity"] == "50", "Exact popularity should be in URL"
    assert "genres" in kwargs, "Genres should be in URL"
    logger.info("test_sync_state_to_url_with_exact_values completed successfully")

def test_get_active_filters_with_exact_values():
    """Tests retrieval of active exact filters."""
    st.session_state.update({
        "selected_genres": ["Action"],
        "year_filter_mode": "exact",
        "exact_year": 2015,
        "rating_filter_mode": "exact",
        "exact_rating": 8.5,
        "popularity_filter_mode": "exact",
        "exact_popularity": 50,
        "last_filter_change": datetime.now().timestamp() - 1.0
    })
    logger.debug("Testing get_active_filters with exact values")
    result = get_active_filters()
    logger.debug(f"Active filters: {result}")
    
    assert result == {
        "genres": ["Action"],
        "year": 2015,
        "rating": 8.5,
        "popularity": 50,
        "ready": True
    }, "Should return exact values with ready=True"
    logger.info("test_get_active_filters_with_exact_values completed successfully")

def test_init_session_state_with_invalid_url_params():
    """Tests initialization with invalid URL parameters."""
    url_params = {
        "genres": "InvalidGenre",
        "year_min": "invalid",
        "year_max": "invalid",
        "rating_min": "invalid",
        "rating_max": "invalid",
        "popularity_min": "invalid",
        "popularity_max": "invalid",
        "exact_year": "invalid",
        "exact_rating": "invalid",
        "exact_popularity": "invalid"
    }
    st.session_state.clear()
    mock_query_params = MagicMock()
    mock_query_params.to_dict.return_value = url_params
    logger.debug("Testing initialization with invalid URL params")
    
    with patch("streamlit.query_params", mock_query_params):
        _init_session_state()
    
    logger.debug(f"Initialized state: {dict(st.session_state)}")
    assert st.session_state["selected_genres"] == ["InvalidGenre"], "Invalid genre should be preserved"
    assert st.session_state["year_range"] == DEFAULT_YEAR_RANGE, "Should fall back to default year range"
    assert st.session_state["rating_range"] == DEFAULT_RATING_RANGE, "Should fall back to default rating range"
    assert st.session_state["popularity_range"] == DEFAULT_POPULARITY_RANGE, "Should fall back to default popularity range"
    assert st.session_state.get("exact_year") is None, "Invalid exact year should be None"
    assert st.session_state.get("exact_rating") is None, "Invalid exact rating should be None"
    assert st.session_state.get("exact_popularity") is None, "Invalid exact popularity should be None"
    logger.info("test_init_session_state_with_invalid_url_params completed successfully")