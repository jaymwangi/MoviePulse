import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import streamlit as st
import os

from session_utils.user_profile import (
    record_movie_view,
    get_badge_progress,
    get_earned_badges,
    load_current_profile,
    save_profile,
    # New preference functions to test
    load_user_preferences,
    save_user_preferences,
    DEFAULT_PREFERENCES,
    get_theme,
    set_theme,
    get_font,
    set_font,
    is_spoiler_free,
    set_spoiler_free,
    is_dyslexia_mode,
    set_dyslexia_mode,
    get_critic_mode_pref,
    set_critic_mode_pref,
    get_preference,
    set_preference,
    initialize_preferences_session
)

# Test Data
SAMPLE_BADGES_CONFIG = {
    "badges": [
        {
            "id": "criterion_explorer",
            "name": "Criterion Explorer",
            "description": "Watch 10 Criterion Collection films",
            "tracking_field": "criterion_views",
            "threshold": 10,
            "tier": "bronze"
        },
        {
            "id": "film_connoisseur",
            "name": "Film Connoisseur",
            "description": "Watch 5 foreign language films",
            "tracking_field": "foreign_views",
            "threshold": 5,
            "tier": "bronze"
        },
        {
            "id": "director_completionist",
            "name": "Director Completionist",
            "description": "Watch 3 films by the same director",
            "tracking_field": "director_completions",
            "threshold": 3,
            "tier": "silver"
        }
    ],
    "tracking_fields": {
        "criterion_views": {
            "source": "watch_history",
            "filter": {"is_criterion": True}
        },
        "foreign_views": {
            "source": "watch_history",
            "filter": {"original_language": {"$not": "en"}}
        },
        "director_completions": {
            "source": "watch_history",
            "aggregate": "director"
        }
    }
}

DEFAULT_PROFILE = {
    "critic_mode": "default",
    "theme": "dark",
    "watchlist": [],
    "view_history": [],
    "starter_pack": None,
    "preferences": {},
    "selected_moods": [],
    "badge_progress": {},
    "earned_badges": []
}

@pytest.fixture
def mock_badges_config():
    """Mock the badge configuration loading"""
    with patch("session_utils.user_profile._load_badges_config", 
              return_value=SAMPLE_BADGES_CONFIG):
        yield

@pytest.fixture
def clean_profile(tmp_path):
    """Provide a clean profile for each test"""
    profile_file = tmp_path / "user_profiles.json"
    with open(profile_file, "w") as f:
        json.dump(DEFAULT_PROFILE, f)
    
    with patch("session_utils.user_profile.PROFILE_FILE", str(profile_file)):
        yield

@pytest.fixture
def temp_preferences_file(tmp_path):
    """Create a temporary preferences file for testing"""
    prefs_file = tmp_path / "user_preferences.json"
    with open(prefs_file, "w") as f:
        json.dump(DEFAULT_PREFERENCES, f)
    
    with patch("session_utils.user_profile.PREFERENCES_FILE", str(prefs_file)):
        yield prefs_file

class MockSessionState:
    """Mock class that supports both dict and attribute access like Streamlit's session_state"""
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'MockSessionState' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        if name == '_data':
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def clear(self):
        self._data.clear()

@pytest.fixture
def mock_streamlit_session():
    """Mock Streamlit session state with proper attribute support"""
    mock_session = MockSessionState()
    with patch("session_utils.user_profile.st.session_state", mock_session):
        yield mock_session

# ===== EXISTING BADGE TESTS (Preserved) =====

def test_record_criterion_view(clean_profile, mock_badges_config):
    """Test recording a Criterion Collection film view"""
    movie_data = {
        "id": 123,
        "title": "Seven Samurai",
        "is_criterion": True,
        "original_language": "ja",
        "vote_average": 8.5,
        "director_ids": [456]
    }
    
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"]["criterion_views"] == 1
    assert profile["view_history"][0]["movie_id"] == 123
    assert profile["view_history"][0]["is_criterion"] is True

def test_non_criterion_view_no_progress(clean_profile, mock_badges_config):
    """Test that non-Criterion films don't increment criterion progress"""
    movie_data = {
        "id": 124,
        "title": "The Dark Knight",
        "is_criterion": False,
        "original_language": "en",
        "vote_average": 9.0,
        "director_ids": [789]
    }
    
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"].get("criterion_views", 0) == 0
    assert profile["view_history"][0]["movie_id"] == 124

def test_foreign_film_progress(clean_profile, mock_badges_config):
    """Test foreign language film tracking"""
    movie_data = {
        "id": 125,
        "title": "Parasite",
        "is_criterion": False,
        "original_language": "ko",
        "vote_average": 8.6,
        "director_ids": [101]
    }
    
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"]["foreign_views"] == 1
    assert profile["view_history"][0]["original_language"] == "ko"

def test_english_film_no_foreign_progress(clean_profile, mock_badges_config):
    """Test English films don't increment foreign views"""
    movie_data = {
        "id": 126,
        "title": "Pulp Fiction",
        "is_criterion": False,
        "original_language": "en",
        "vote_average": 8.9,
        "director_ids": [202]
    }
    
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"].get("foreign_views", 0) == 0

def test_director_completion_progress(clean_profile, mock_badges_config):
    """Test director-specific tracking"""
    director_id = 456
    movie_data = {
        "id": 127,
        "title": "The Godfather",
        "is_criterion": True,
        "original_language": "en",
        "vote_average": 9.2,
        "director_ids": [director_id]
    }
    
    # Record 2 views for this director
    record_movie_view(movie_data)
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"][f"director_{director_id}"] == 2
    assert profile["badge_progress"]["criterion_views"] == 2

def test_multiple_directors_tracking(clean_profile, mock_badges_config):
    """Test movies with multiple directors track each one"""
    movie_data = {
        "id": 128,
        "title": "The Matrix",
        "is_criterion": False,
        "original_language": "en",
        "vote_average": 8.7,
        "director_ids": [303, 404]
    }
    
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert profile["badge_progress"]["director_303"] == 1
    assert profile["badge_progress"]["director_404"] == 1

def test_badge_earned_notification(clean_profile, mock_badges_config):
    """Test badge earning triggers notification"""
    movie_data = {
        "id": 129,
        "title": "Citizen Kane",
        "is_criterion": True,
        "original_language": "en",
        "vote_average": 8.3,
        "director_ids": [505]
    }
    
    # Set up profile with 9/10 criterion views
    profile = load_current_profile()
    profile["badge_progress"]["criterion_views"] = 9
    save_profile(profile)
    
    # Record the 10th view
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert "criterion_explorer" in profile["earned_badges"]
    assert profile["badge_progress"]["criterion_views"] == 10

def test_view_history_limits(clean_profile, mock_badges_config):
    """Test view history maintains 100-entry limit"""
    movie_data = {
        "id": 130,
        "title": "New Movie",
        "is_criterion": False,
        "original_language": "en",
        "vote_average": 7.5,
        "director_ids": [606]
    }
    
    # Set up profile with 100 existing views (movie_ids 1-100)
    profile = load_current_profile()
    profile["view_history"] = [{"movie_id": i} for i in range(1, 101)]  # 1-100
    save_profile(profile)
    
    # Record new view
    record_movie_view(movie_data)
    
    profile = load_current_profile()
    assert len(profile["view_history"]) == 100
    assert profile["view_history"][0]["movie_id"] == 130  # Newest first
    assert profile["view_history"][-1]["movie_id"] == 99  # Oldest remaining entry

def test_get_badge_progress(clean_profile, mock_badges_config):
    """Test progress reporting for all badges"""
    # Set up test progress
    profile = load_current_profile()
    profile["badge_progress"] = {
        "criterion_views": 5,
        "foreign_views": 2,
        "director_707": 1,
        "director_808": 3
    }
    save_profile(profile)
    
    progress = get_badge_progress()
    
    assert progress["criterion_explorer"] == (5, 10)
    assert progress["film_connoisseur"] == (2, 5)
    assert progress["director_completionist"] == (3, 3)  # One director completed

def test_get_earned_badges(clean_profile, mock_badges_config):
    """Test retrieval of earned badges"""
    # Set up earned badges
    profile = load_current_profile()
    profile["earned_badges"] = ["criterion_explorer", "film_connoisseur"]  # Fixed spelling: connoisseur
    save_profile(profile)
    
    earned = get_earned_badges()
    
    assert len(earned) == 2
    assert any(b["id"] == "criterion_explorer" for b in earned)
    assert any(b["id"] == "film_connoisseur" for b in earned)

def test_composite_badge_progress(clean_profile, mock_badges_config):
    """Test composite badge progress calculation"""
    # Add composite badge to config
    SAMPLE_BADGES_CONFIG["badges"].append({
        "id": "cinephile_master",
        "name": "Cinephile Master",
        "description": "Earn all bronze badges",
        "composite": True,
        "requirements": ["criterion_explorer", "film_connoisseur"],
        "tier": "gold"
    })
    
    # Set up partial progress
    profile = load_current_profile()
    profile["earned_badges"] = ["criterion_explorer"]
    save_profile(profile)
    
    progress = get_badge_progress()
    
    assert progress["cinephile_master"] == (1, 2)

# ===== NEW PREFERENCE TESTS =====

class TestUserPreferences:
    """Test suite for user preference management"""
    
    def _initialize_session_state(self, mock_session):
        """Initialize session state with default values"""
        mock_session.theme = "dark"
        mock_session.font = "default"
        mock_session.spoiler_free = False
        mock_session.dyslexia_mode = False
        mock_session.critic_mode = "default"
    
    def test_load_user_preferences_defaults(self, temp_preferences_file):
        """Test loading preferences when file doesn't exist"""
        # Remove the file to test default creation
        os.remove(temp_preferences_file)
        
        with patch("session_utils.user_profile.save_user_preferences") as mock_save:
            prefs = load_user_preferences()
            
            # Should return defaults
            assert prefs == DEFAULT_PREFERENCES
            # Should attempt to save defaults
            mock_save.assert_called_once_with(DEFAULT_PREFERENCES.copy())
    
    def test_load_user_preferences_existing(self, temp_preferences_file):
        """Test loading preferences from existing file"""
        test_prefs = {
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True,
            'dyslexia_mode': True,
            'critic_mode': 'strict'
        }
        
        # Write test preferences to file
        with open(temp_preferences_file, 'w') as f:
            json.dump(test_prefs, f)
        
        prefs = load_user_preferences()
        
        # Should load the test preferences
        assert prefs == test_prefs
    
    def test_load_user_preferences_corrupted(self, temp_preferences_file):
        """Test loading preferences from corrupted file"""
        # Write invalid JSON to file
        with open(temp_preferences_file, 'w') as f:
            f.write('{invalid json')
        
        prefs = load_user_preferences()
        
        # Should return defaults on error
        assert prefs == DEFAULT_PREFERENCES
    
    def test_save_user_preferences_success(self, temp_preferences_file):
        """Test successfully saving preferences"""
        test_prefs = {
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True,
            'dyslexia_mode': True,
            'critic_mode': 'strict',
            'notifications_enabled': True
        }
        
        # Save preferences
        save_user_preferences(test_prefs)
        
        # Load and verify they were saved correctly
        with open(temp_preferences_file, 'r') as f:
            saved_prefs = json.load(f)
        
        # Should match what we saved (with validation)
        expected_prefs = DEFAULT_PREFERENCES.copy()
        expected_prefs.update({
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True,
            'dyslexia_mode': True,
            'critic_mode': 'strict'
        })
        assert saved_prefs == expected_prefs
    
    def test_save_user_preferences_invalid_data(self, temp_preferences_file):
        """Test saving preferences with invalid data types"""
        invalid_prefs = {
            'theme': 123,  # Should be string
            'font': ['invalid'],  # Should be string
            'spoiler_free': 'not boolean',  # Should be boolean
            'critic_mode': 456  # Should be string
        }
        
        # Save should handle invalid data gracefully
        save_user_preferences(invalid_prefs)
        
        # Load and verify defaults were used for invalid values
        with open(temp_preferences_file, 'r') as f:
            saved_prefs = json.load(f)
        
        # Invalid values should be replaced with defaults
        assert saved_prefs == DEFAULT_PREFERENCES
    
    def test_preference_getter_setter_functions(self, temp_preferences_file, mock_streamlit_session):
        """Test all the individual preference getter/setter functions"""
        # Initialize session state first
        self._initialize_session_state(mock_streamlit_session)
        
        # Test theme functions
        set_theme('light')
        assert get_theme() == 'light'
        
        # Test font functions
        set_font('dyslexia')
        assert get_font() == 'dyslexia'
        
        # Test spoiler free functions
        set_spoiler_free(True)
        assert is_spoiler_free() == True
        
        # Test dyslexia mode functions
        set_dyslexia_mode(True)
        assert is_dyslexia_mode() == True
        
        # Test critic mode functions
        set_critic_mode_pref('strict')
        assert get_critic_mode_pref() == 'strict'
    
    def test_preference_validation(self, temp_preferences_file, mock_streamlit_session):
        """Test that preference setters validate input values"""
        # Initialize session state first
        self._initialize_session_state(mock_streamlit_session)
        
        # Test invalid theme
        original_theme = get_theme()
        set_theme('invalid_theme')  # Should not change
        assert get_theme() == original_theme
        
        # Test invalid font
        original_font = get_font()
        set_font('invalid_font')  # Should not change
        assert get_font() == original_font
        
        # Test invalid critic mode
        original_critic_mode = get_critic_mode_pref()
        set_critic_mode_pref('invalid_mode')  # Should not change
        assert get_critic_mode_pref() == original_critic_mode
        
    def test_session_state_integration(self, temp_preferences_file, mock_streamlit_session):
        """Test that preferences are properly stored in session state"""
        # Don't initialize session state first - let the functions do it
        
        # Initially not in session state
        assert not hasattr(mock_streamlit_session, 'theme')
        
        # First call should load from file and set session state
        theme = get_theme()
        assert hasattr(mock_streamlit_session, 'theme')
        assert mock_streamlit_session.theme == theme
        
        # Setter should update session state
        set_theme('light')
        assert mock_streamlit_session.theme == 'light'
    
    def test_save_reload_cycle(self, temp_preferences_file, mock_streamlit_session):
        """Test the complete save → reload cycle"""
        # Don't initialize session state first - let the functions do it
        
        # Set new preferences
        test_prefs = {
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True,
            'dyslexia_mode': True,
            'critic_mode': 'strict'
        }
        
        # Save preferences
        save_user_preferences(test_prefs)
        
        # Clear session state to simulate app restart (no need to delete attributes)
        mock_streamlit_session.clear()
        
        # Load preferences again
        reloaded_prefs = load_user_preferences()
        
        # Should match what we saved
        expected_prefs = DEFAULT_PREFERENCES.copy()
        expected_prefs.update(test_prefs)
        assert reloaded_prefs == expected_prefs
        
        # Session state should be updated when getters are called
        assert get_theme() == 'light'
        assert get_font() == 'dyslexia'
        assert is_spoiler_free() == True
        assert is_dyslexia_mode() == True
        assert get_critic_mode_pref() == 'strict'
    
    def test_general_preference_functions(self, temp_preferences_file, mock_streamlit_session):
        """Test the general get_preference and set_preference functions"""
        # Initialize session state first
        self._initialize_session_state(mock_streamlit_session)
        
        # Test setting a preference
        set_preference('theme', 'light')
        assert get_preference('theme') == 'light'
        
        # Test getting default for non-existent preference
        assert get_preference('non_existent', 'default_value') == 'default_value'
        
        # Test invalid preference key
        set_preference('invalid_key', 'value')  # Should be ignored
        assert get_preference('invalid_key') is None
    

    def test_initialize_preferences_session(self, temp_preferences_file, mock_streamlit_session):
        """Test session initialization function"""
        # Don't initialize session state first - let the function do it
        
        # Set some preferences first
        test_prefs = {
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True
        }
        save_user_preferences(test_prefs)
        
        # Clear session state
        mock_streamlit_session.clear()
        
        # Initialize session
        initialize_preferences_session()
        
        # Session state should be populated
        assert mock_streamlit_session.theme == 'light'
        assert mock_streamlit_session.font == 'dyslexia'
        assert mock_streamlit_session.spoiler_free == True

if __name__ == '__main__':
    pytest.main([__file__, '-v'])