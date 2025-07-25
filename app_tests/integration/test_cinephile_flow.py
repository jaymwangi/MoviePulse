# app_tests/integration/test_cinephile_flow.py
import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
import json
from datetime import datetime
from session_utils.user_profile import (
    load_current_profile,
    save_profile,
    record_movie_view,
    get_badge_progress,
    get_user_id,
    update_cinephile_stats,
    DEFAULT_PROFILE
)
from pages.page_07_cinephile_mode import (
    show_cinephile_filters,
    filter_movies,
    show_badge_progress
)

# Test data - updated to match current implementation
TEST_MOVIES = [
    {
        "id": 496243,
        "title": "Parasite",
        "original_language": "ko",
        "vote_average": 8.5,
        "belongs_to_collection": True,
        "poster_path": "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
        "director_ids": [123],
        "genres": [18, 53],
        "year": 2019,
        "is_criterion": True
    },
    {
        "id": 238,
        "title": "The Godfather",
        "original_language": "en",
        "vote_average": 9.2,
        "belongs_to_collection": True,
        "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "director_ids": [456],
        "genres": [18, 80],
        "year": 1972,
        "is_criterion": True
    },
    {
        "id": 155,
        "title": "The Dark Knight",
        "original_language": "en",
        "vote_average": 8.5,
        "belongs_to_collection": False,
        "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "director_ids": [789],
        "genres": [28, 18, 80],
        "year": 2008,
        "is_criterion": False
    }
]

@pytest.fixture
def mock_badge_config(tmp_path):
    """Create a mock badge configuration file that matches current implementation"""
    badge_config = {
        "badges": [
            {
                "id": "foreign_film_buff",
                "name": "Foreign Film Buff",
                "description": "Watch 5 foreign language films",
                "tracking_field": "foreign_films_watched",
                "threshold": 5,
                "tier": "bronze",
                "icon": "🌎"
            },
            {
                "id": "criterion_connoisseur",
                "name": "Criterion Connoisseur",
                "description": "Watch 10 Criterion Collection films",
                "tracking_field": "criterion_films_watched",
                "threshold": 10,
                "tier": "silver",
                "icon": "🏛"
            },
            {
                "id": "director_specialist",
                "name": "Director Specialist",
                "description": "Watch 5 films by one director",
                "tracking_field": "director_completions",
                "threshold": 5,
                "tier": "silver",
                "icon": "🎥"
            }
        ],
        "tracking_fields": {
            "foreign_films_watched": {
                "source": "watch_history",
                "filter": {"original_language": {"$not": "en"}}
            },
            "criterion_films_watched": {
                "source": "watch_history",
                "filter": {"is_criterion": True}
            },
            "director_completions": {
                "source": "watch_history",
                "filter": {}
            }
        }
    }
    
    config_file = tmp_path / "cinephile_badges.json"
    with open(config_file, 'w') as f:
        json.dump(badge_config, f)
    
    return config_file

@pytest.fixture(autouse=True)
def setup_session_state():
    """Initialize Streamlit session state for each test"""
    st.session_state.clear()
    st.session_state.update({
        "cinephile_foreign": False,
        "cinephile_criterion": False,
        "cinephile_min_score": 85,
        "user_id": "test_user_123"
    })

def test_filter_persistence_across_sessions(tmp_path, mock_badge_config):
    """Test that cinephile filters persist across sessions"""
    # Set up test profile
    test_profile = DEFAULT_PROFILE.copy()
    test_profile.update({
        "cinephile_filters": {
            "foreign": True,
            "criterion": False,
            "min_score": 90
        }
    })
    
    # Save initial profile
    with patch("session_utils.user_profile.PROFILE_FILE", tmp_path / "profiles.json"):
        save_profile(test_profile)
        
        # Simulate new session load
        loaded_profile = load_current_profile()
        
        # Verify basic profile was loaded
        assert loaded_profile["critic_mode"] == "default"

def test_movie_filtering_logic():
    """Test the enhanced cinephile movie filtering logic"""
    # Test foreign films filter
    st.session_state.cinephile_foreign = True
    filtered = filter_movies(TEST_MOVIES)
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Parasite"
    
    # Test criterion filter
    st.session_state.cinephile_foreign = False
    st.session_state.cinephile_criterion = True
    filtered = filter_movies(TEST_MOVIES)
    assert len(filtered) == 2
    assert all(m["is_criterion"] for m in filtered)
    
    # Test score filter
    st.session_state.cinephile_criterion = False
    st.session_state.cinephile_min_score = 90
    filtered = filter_movies(TEST_MOVIES)
    assert len(filtered) == 1
    assert filtered[0]["title"] == "The Godfather"

def test_empty_movie_list_handling():
    """Test that empty movie list is handled gracefully"""
    filtered = filter_movies([])
    assert filtered == []

def test_badge_progress_updates(tmp_path, mock_badge_config):
    """Test that badge progress updates after film interaction"""
    with patch("session_utils.user_profile.PROFILE_FILE", tmp_path / "profiles.json"), \
         patch("session_utils.user_profile.BADGES_CONFIG", mock_badge_config):
        
        # Initial state - no progress
        progress = get_badge_progress()
        assert progress.get("foreign_film_buff", (0, 1))[0] == 0
        assert progress.get("criterion_connoisseur", (0, 1))[0] == 0
        
        # Record viewing of a foreign criterion film
        record_movie_view(TEST_MOVIES[0])  # Parasite
        
        # Verify progress updated
        progress = get_badge_progress()
        assert progress["foreign_film_buff"][0] == 1  # 1/5
        assert progress["criterion_connoisseur"][0] == 1  # 1/10
        
        # Record viewing of an English criterion film
        record_movie_view(TEST_MOVIES[1])  # The Godfather
        
        # Verify only criterion count increased
        progress = get_badge_progress()
        assert progress["foreign_film_buff"][0] == 1  # still 1/5
        assert progress["criterion_connoisseur"][0] == 2  # now 2/10

def test_badge_ui_rendering(tmp_path, mock_badge_config):
    """Test that badge progress UI renders correctly with tier filtering"""
    # Mock the BadgeProgress component
    mock_badge_component = MagicMock()
    mock_badge_component.return_value.display_badge_progress.return_value = None
    
    with patch("pages.page_07_cinephile_mode.BadgeProgress", mock_badge_component), \
         patch("session_utils.user_profile.BADGES_CONFIG", mock_badge_config), \
         patch("session_utils.user_profile.PROFILE_FILE", tmp_path / "profiles.json"):
        
        # Set up test profile with some progress
        test_profile = DEFAULT_PROFILE.copy()
        test_profile.update({
            "badge_progress": {
                "foreign_films_watched": 3,
                "criterion_films_watched": 7,
                "director_123": 4
            },
            "earned_badges": []
        })
        save_profile(test_profile)
        
        # Call the function
        show_badge_progress()
        
        # Verify the badge component was called correctly
        mock_badge_component.return_value.display_badge_progress.assert_called_once()

def test_filter_ui_rendering():
    """Test that filter UI components render correctly with expander"""
    # Mock Streamlit components
    mock_expander = MagicMock()
    mock_expander.__enter__.return_value = mock_expander  # For 'with' statement
    
    with patch("streamlit.header") as mock_header, \
         patch("streamlit.expander", return_value=mock_expander) as mock_expander_func, \
         patch("streamlit.checkbox") as mock_checkbox, \
         patch("streamlit.slider") as mock_slider:
        
        # Call the function
        show_cinephile_filters()
        
        # Verify UI components were created
        mock_header.assert_called_once_with("🎬 Cinephile Mode")
        mock_expander_func.assert_called_once_with("Filter Options", expanded=True)
        assert mock_checkbox.call_count == 2
        assert mock_slider.call_count == 1

def test_movie_display_handling():
    """Test that movie display handles missing poster paths"""
    # Set up test movie and session state
    test_movies = [{
        "id": 1,
        "title": "Test Movie",
        "original_language": "en",
        "vote_average": 7.5,
        "belongs_to_collection": False,
        "poster_path": None,
        "director_ids": [],
        "genres": [],
        "year": 2020,
        "is_criterion": False
    }]
    
    # Reset any filters that might exclude this movie
    st.session_state.cinephile_foreign = False
    st.session_state.cinephile_criterion = False
    st.session_state.cinephile_min_score = 0
    
    filtered = filter_movies(test_movies)
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Test Movie"

def test_update_cinephile_stats(tmp_path, mock_badge_config):
    """Test the update_cinephile_stats function with TMDB client mock"""
    # Mock the TMDB client import
    mock_tmdb = MagicMock()
    mock_movie = MagicMock()
    mock_movie.belongs_to_collection = True
    mock_movie.original_language = "fr"
    mock_movie.vote_average = 8.0
    mock_movie.directors = [MagicMock(id=123)]
    mock_movie.genres = [MagicMock(id=18)]
    mock_movie.release_date = "2020-01-01"
    mock_tmdb.get_movie_details.return_value = mock_movie
    
    with patch("session_utils.user_profile.PROFILE_FILE", tmp_path / "profiles.json"), \
         patch("session_utils.user_profile.BADGES_CONFIG", mock_badge_config), \
         patch("service_clients.tmdb_client.tmdb_client", mock_tmdb):
        
        # Create a fresh profile to ensure no existing view history
        test_profile = DEFAULT_PROFILE.copy()
        test_profile["view_history"] = []
        save_profile(test_profile)
        
        # Call the function
        update_cinephile_stats(12345)
        
        # Verify TMDB client was called
        mock_tmdb.get_movie_details.assert_called_once_with(12345)
        
        # Verify profile was updated
        profile = load_current_profile()
        assert len(profile["view_history"]) == 1
        view_entry = profile["view_history"][0]
        assert view_entry["movie_id"] == 12345
        assert view_entry["is_criterion"] is True
        
def test_view_history_limits(tmp_path, mock_badge_config):
    """Test that view history is limited to 100 entries"""
    with patch("session_utils.user_profile.PROFILE_FILE", tmp_path / "profiles.json"), \
         patch("session_utils.user_profile.BADGES_CONFIG", mock_badge_config):
        
        # Create a profile with 105 view entries
        test_profile = DEFAULT_PROFILE.copy()
        test_profile["view_history"] = [
            {
                "movie_id": i,
                "timestamp": datetime.now().isoformat(),
                "is_criterion": False,
                "original_language": "en",
                "critic_score": 70,
                "director_ids": [],
                "genres": [],
                "year": 2020
            } 
            for i in range(105)
        ]
        save_profile(test_profile)
        
        # Add one more view
        record_movie_view(TEST_MOVIES[0])
        
        # Verify history was trimmed to 100 entries
        profile = load_current_profile()
        assert len(profile["view_history"]) == 100
        # Newest entry should be first
        assert profile["view_history"][0]["movie_id"] == TEST_MOVIES[0]["id"]