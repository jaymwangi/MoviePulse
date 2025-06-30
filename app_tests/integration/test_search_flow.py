import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
import json
from datetime import datetime

# Import components
from ui_components.SidebarFilters import (
    render_sidebar_filters,
    get_active_filters,
    _init_session_state,
    DEFAULT_YEAR_RANGE,
    DEFAULT_RATING_RANGE
)
from service_clients.tmdb_client import tmdb_client, FallbackStrategy

# Mock data
MOCK_GENRES = [
    {"id": 28, "name": "Action"},
    {"id": 12, "name": "Adventure"},
    {"id": 16, "name": "Animation"}
]

MOCK_MOVIES = [
    {
        "id": 1,
        "title": "Test Movie 1",
        "release_date": "2020-01-01",
        "vote_average": 8.5,
        "genre_ids": [28, 12]
    },
    {
        "id": 2,
        "title": "Test Movie 2",
        "release_date": "2018-01-01",
        "vote_average": 7.0,
        "genre_ids": [16]
    }
]

@pytest.fixture
def mock_genres_file(tmp_path):
    """Create a temporary genres.json file for testing"""
    genres_file = tmp_path / "genres.json"
    genres_file.write_text(json.dumps(MOCK_GENRES))
    return str(genres_file)

@pytest.fixture
def setup_session_state():
    """Initialize a clean session state with all required fields"""
    st.session_state.clear()
    st.session_state.update({
        "selected_genres": [],
        "year_range": DEFAULT_YEAR_RANGE,
        "rating_range": DEFAULT_RATING_RANGE,
        "popularity_range": (0, 100),
        "year_filter_mode": "range",
        "rating_filter_mode": "range",
        "popularity_filter_mode": "range",
        "last_filter_change": 0,
        "filter_init_complete": True,
        "global_search_query": "test",
        "current_page": 1,
        "search_fallback_strategy": FallbackStrategy.RELAX_GRADUAL,
        "filter_execution_in_progress": False,
        "exact_year": None,
        "exact_rating": None,
        "exact_popularity": None
    })

@pytest.fixture
def mock_streamlit_components():
    """Mock all Streamlit UI components with proper formatting support"""
    # Create mock columns with button support
    mock_col = MagicMock()
    mock_button = MagicMock()
    mock_button.__format__ = lambda self, format_spec: "MockButton"  # Add formatting support
    mock_col.button.return_value = mock_button
    
    # Create mock slider that returns test values
    mock_slider = MagicMock()
    mock_slider.return_value = (2010, 2020)
    mock_slider.__format__ = lambda self, format_spec: "2010-2020"  # Add formatting support
    
    # Create mock expander
    mock_expander = MagicMock()
    mock_expander.__enter__.return_value = MagicMock()
    
    with patch('streamlit.columns', return_value=[mock_col, mock_col]), \
         patch('streamlit.expander', return_value=mock_expander), \
         patch('streamlit.multiselect', return_value=["Action"]), \
         patch('streamlit.button', return_value=False), \
         patch('streamlit.slider', mock_slider), \
         patch('streamlit.number_input', return_value=2018), \
         patch('streamlit.markdown'), \
         patch('streamlit.divider'), \
         patch('streamlit.spinner'), \
         patch('streamlit.toast'):
        yield

def test_search_flow_with_filters(mock_genres_file, setup_session_state, mock_streamlit_components):
    """Test complete flow from UI filters to API call to results rendering"""
    # Mock the TMDB client response
    with patch.object(tmdb_client, 'search_movies', return_value=(MOCK_MOVIES, 1)) as mock_search:
        with patch("ui_components.SidebarFilters.GENRES_FILE", mock_genres_file):
            # Render sidebar with test filters
            render_sidebar_filters()
            
            # Simulate filter changes
            st.session_state.update({
                "selected_genres": ["Action"],
                "year_range": (2010, 2020),
                "rating_range": (8.0, 10.0)
            })
            
            # Get active filters and trigger search
            filters = get_active_filters()
            results, total_pages = tmdb_client.search_movies(
                query=st.session_state["global_search_query"],
                filters=filters,
                fallback_strategy=st.session_state["search_fallback_strategy"]
            )
            
            # Verify API was called with correct parameters
            mock_search.assert_called_once()
            args, kwargs = mock_search.call_args
            assert kwargs["query"] == "test"
            assert kwargs["filters"]["genres"] == ["Action"]
            assert kwargs["filters"]["year_range"] == (2010, 2020)
            assert kwargs["filters"]["rating_range"] == (8.0, 10.0)
            
            # Verify results processing
            assert len(results) == 2
            assert isinstance(results[0], dict)
            assert isinstance(total_pages, int)

def test_fallback_strategy_application(mock_genres_file, setup_session_state, mock_streamlit_components):
    """Test that fallback strategies are properly applied"""
    # Mock the TMDB client
    with patch.object(tmdb_client, 'search_movies') as mock_search:
        # Configure different responses based on filters
        def search_side_effect(query, filters, fallback_strategy):
            if filters.get("genres") == ["Nonexistent Genre"]:
                return ([], 0)  # Strict filters return nothing
            return (MOCK_MOVIES, 1)  # Relaxed filters return results
            
        mock_search.side_effect = search_side_effect
        
        with patch("ui_components.SidebarFilters.GENRES_FILE", mock_genres_file):
            # Set up test with strict filters
            st.session_state.update({
                "selected_genres": ["Nonexistent Genre"],
                "year_range": (1900, 1901),
                "rating_range": (9.9, 10.0),
                "search_fallback_strategy": FallbackStrategy.RELAX_GRADUAL
            })
            
            # Get active filters
            filters = get_active_filters()
            
            # First search attempt (should return no results)
            results, total_pages = tmdb_client.search_movies(
                query="test",
                filters=filters,
                fallback_strategy=st.session_state["search_fallback_strategy"]
            )
            
            # Verify first call used strict filters
            assert mock_search.call_count == 1
            args, kwargs = mock_search.call_args
            assert kwargs["filters"]["genres"] == ["Nonexistent Genre"]
            
            # Verify no results
            assert len(results) == 0
            assert total_pages == 0
            
            # Now test the UI would trigger a fallback search (this part would be in your UI code)
            # Here we simulate what the UI would do when no results are found
            if len(results) == 0 and st.session_state["search_fallback_strategy"] != FallbackStrategy.NONE:
                # Relax filters according to strategy
                relaxed_filters = filters.copy()
                relaxed_filters.pop("genres", None)  # Remove genre filter
                
                # Second search attempt with relaxed filters
                results, total_pages = tmdb_client.search_movies(
                    query="test",
                    filters=relaxed_filters,
                    fallback_strategy=st.session_state["search_fallback_strategy"]
                )
                
                # Verify second call
                assert mock_search.call_count == 2
                args, kwargs = mock_search.call_args
                assert "genres" not in kwargs["filters"]  # Genre filter removed
                
                # Verify we got results after fallback
                assert len(results) == 2
                assert total_pages == 1
            

def test_filter_to_api_parameter_mapping(mock_genres_file, setup_session_state, mock_streamlit_components):
    """Test that UI filters are correctly mapped to API parameters"""
    # Mock TMDB client
    with patch.object(tmdb_client, 'search_movies', return_value=([], 0)), \
         patch("ui_components.SidebarFilters.GENRES_FILE", mock_genres_file):
        
        # Set up test filters
        st.session_state.update({
            "selected_genres": ["Action", "Adventure"],
            "year_range": (2015, 2020),
            "rating_range": (7.5, 9.0),
            "exact_year": 2018,
            "year_filter_mode": "exact"
        })
        
        # Get active filters
        filters = get_active_filters()
        
        # Verify parameter mapping
        assert filters["genres"] == ["Action", "Adventure"]
        assert "year_range" not in filters  # Should use exact year instead
        assert filters["year"] == 2018
        assert filters["rating_range"] == (7.5, 9.0)