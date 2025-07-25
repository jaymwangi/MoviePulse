import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from datetime import datetime

from session_utils.user_profile import (
    record_movie_view,
    get_badge_progress,
    get_earned_badges,
    load_current_profile,
    save_profile
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
    profile["earned_badges"] = ["criterion_explorer", "film_connoisseur"]
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