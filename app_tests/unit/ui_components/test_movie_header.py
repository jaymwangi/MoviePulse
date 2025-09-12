# app_tests/unit/ui_components/test_movie_header.py

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add the app_ui directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from app_ui.components.MovieHeader import MovieHeader, format_rating, get_rating_class

# Mock Streamlit components to avoid rendering during tests
st.container = MagicMock()
st.markdown = MagicMock()
st.error = MagicMock()

def test_format_rating():
    """Test the format_rating function"""
    # Test float rating
    assert format_rating(8.5) == "8.5/10"
    
    # Test integer rating
    assert format_rating(7) == "7.0/10"
    
    # Test string rating
    assert format_rating("N/A") == "N/A"
    
    # Test None rating
    assert format_rating(None) == "None"

def test_get_rating_class():
    """Test the get_rating_class function"""
    # Test excellent rating
    assert get_rating_class(9.0) == "rating-excellent"
    assert get_rating_class(8.0) == "rating-excellent"
    
    # Test good rating
    assert get_rating_class(7.9) == "rating-good"
    assert get_rating_class(6.0) == "rating-good"
    
    # Test average rating
    assert get_rating_class(5.9) == "rating-average"
    assert get_rating_class(4.0) == "rating-average"
    
    # Test poor rating
    assert get_rating_class(3.9) == "rating-poor"
    assert get_rating_class(2.0) == "rating-poor"
    
    # Test unknown rating type
    assert get_rating_class("N/A") == "rating-unknown"
    assert get_rating_class(None) == "rating-unknown"

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_with_valid_data(mock_load_css):
    """Test MovieHeader with complete valid data"""
    movie_data = {
        "title": "The Shawshank Redemption",
        "year": 1994,
        "rating": 9.3,
        "tagline": "Fear can hold you prisoner. Hope can set you free.",
        "genres": ["Drama", "Crime"]
    }
    
    # Call the component
    MovieHeader(movie_data)
    
    # Verify CSS was loaded
    mock_load_css.assert_called_once_with("components.css")
    
    # Verify markdown was called for the container
    assert st.markdown.call_count >= 4  # Container start, title, rating, tagline, container end

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_minimal_data(mock_load_css):
    """Test MovieHeader with minimal data"""
    movie_data = {
        "title": "Inception",
        "year": 2010
    }
    
    # Call the component
    MovieHeader(movie_data)
    
    # Verify CSS was loaded
    mock_load_css.assert_called_once_with("components.css")
    
    # Should not call error
    st.error.assert_not_called()

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_no_data(mock_load_css):
    """Test MovieHeader with no data"""
    # Reset mock call counts
    st.error.reset_mock()
    
    # Call the component with None
    MovieHeader(None)
    
    # Should call error at least once (might be called multiple times due to validation)
    assert st.error.call_count >= 1
    error_calls = [call_args[0][0] for call_args in st.error.call_args_list]
    assert any("Invalid movie data provided to MovieHeader" in call for call in error_calls)

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_empty_dict(mock_load_css):
    """Test MovieHeader with empty dictionary"""
    # Reset mock call counts
    st.error.reset_mock()
    
    # Call the component with empty dict
    MovieHeader({})
    
    # Should call error at least once (might be called multiple times due to validation)
    assert st.error.call_count >= 1
    error_calls = [call_args[0][0] for call_args in st.error.call_args_list]
    assert any("Invalid movie data provided to MovieHeader" in call for call in error_calls)

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_variants(mock_load_css):
    """Test MovieHeader with different variants"""
    movie_data = {
        "title": "The Dark Knight",
        "year": 2008,
        "rating": 9.0,
        "tagline": "Why So Serious?",
        "genres": ["Action", "Crime", "Drama"]
    }
    
    # Reset mocks before testing variants
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test default variant
    MovieHeader(movie_data, variant="default")
    mock_load_css.assert_called_once_with("components.css")
    
    # Reset for next test
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test compact variant
    MovieHeader(movie_data, variant="compact")
    mock_load_css.assert_called_once_with("components.css")
    
    # Reset for next test
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test detailed variant
    MovieHeader(movie_data, variant="detailed")
    mock_load_css.assert_called_once_with("components.css")

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_hide_elements(mock_load_css):
    """Test MovieHeader with hidden elements"""
    movie_data = {
        "title": "Pulp Fiction",
        "year": 1994,
        "rating": 8.9,
        "tagline": "Just because you are a character doesn't mean you have character."
    }
    
    # Reset mocks
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test without tagline
    MovieHeader(movie_data, show_tagline=False)
    mock_load_css.assert_called_once_with("components.css")
    
    # Reset mocks
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test without rating
    MovieHeader(movie_data, show_rating=False)
    mock_load_css.assert_called_once_with("components.css")
    
    # Reset mocks
    mock_load_css.reset_mock()
    st.markdown.reset_mock()
    
    # Test without both
    MovieHeader(movie_data, show_tagline=False, show_rating=False)
    mock_load_css.assert_called_once_with("components.css")

@patch('app_ui.components.MovieHeader.load_css')
def test_movie_header_different_ratings(mock_load_css):
    """Test MovieHeader with different rating values"""
    test_cases = [
        {"title": "Excellent", "rating": 9.5},
        {"title": "Good", "rating": 7.2},
        {"title": "Average", "rating": 5.5},
        {"title": "Poor", "rating": 3.1},
        {"title": "String Rating", "rating": "N/A"},
        {"title": "No Rating", "rating": None}
    ]
    
    for movie_data in test_cases:
        # Reset mocks for each test case
        mock_load_css.reset_mock()
        st.markdown.reset_mock()
        
        MovieHeader(movie_data)
        mock_load_css.assert_called_once_with("components.css")

def test_movie_header_import():
    """Test that the MovieHeader component can be imported correctly"""
    # This test verifies there are no import issues
    from app_ui.components.MovieHeader import MovieHeader
    assert callable(MovieHeader)

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])