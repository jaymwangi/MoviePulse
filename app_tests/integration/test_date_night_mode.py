import pytest
from unittest.mock import patch, MagicMock
import json
import streamlit as st
from datetime import datetime

from session_utils.state_tracker import (
    initiate_date_night,
    is_date_night_active,
    end_date_night
)
from ai_smart_recommender.user_personalization.date_night_blender import (
    blend_packs,
    save_date_session,
    weighted_avg_moods
)

# Test Data
@pytest.fixture
def sample_packs():
    return {
        "romcom": {
            "name": "Romantic Comedy",
            "movies": [1, 2, 3],
            "moods": {"happy": 0.8, "funny": 0.7}
        },
        "action": {
            "name": "Action Pack",
            "movies": [4, 5, 6],
            "moods": {"excited": 0.9, "happy": 0.5}
        }
    }

@pytest.fixture
def mock_session(tmp_path):
    sessions_file = tmp_path / "date_sessions.json"
    with patch("ai_smart_recommender.user_personalization.date_night_blender.Path") as mock_path:
        mock_path.return_value = sessions_file
        yield sessions_file

# Unit Tests
def test_weighted_avg_moods():
    """Test mood score blending"""
    moods_a = {"happy": 0.8, "funny": 0.5}
    moods_b = {"happy": 0.4, "excited": 0.9}
    
    blended = weighted_avg_moods(moods_a, moods_b)
    
    assert blended["happy"] == 0.6  # (0.8 + 0.4)/2
    assert blended["funny"] == 0.25 # (0.5 + 0)/2
    assert blended["excited"] == 0.45 # (0 + 0.9)/2


# Integration Tests
def test_initiate_date_night(sample_packs, mock_session):
    """Test full date night activation flow"""
    # Initial state
    assert not is_date_night_active()
    
    # Activate
    initiate_date_night(sample_packs["romcom"], sample_packs["action"])
    
    # Verify session state
    assert is_date_night_active()
    assert "blended_prefs" in st.session_state
    assert st.session_state.original_packs["pack_a"]["name"] == "Romantic Comedy"

def test_end_date_night(sample_packs):
    """Test session termination"""
    initiate_date_night(sample_packs["romcom"], sample_packs["action"])
    assert is_date_night_active()
    
    end_date_night()
    assert not is_date_night_active()
    assert "blended_prefs" not in st.session_state

# Manual Test Simulation
@pytest.mark.manual
def test_manual_date_night_flow(sample_packs, tmp_path):
    """Manual Test Checklist:
    1. Launch app and navigate to Date Night UI
    2. Select two different packs
    3. Verify:
       - Session state updates correctly
       - Recommendations change
       - Session appears in date_sessions.json
    4. End session and verify cleanup
    """
    # Mock UI selection
    pack_a = sample_packs["romcom"]
    pack_b = sample_packs["action"]
    
    # Create a real session file for manual testing
    sessions_file = tmp_path / "date_sessions.json"
    with patch("ai_smart_recommender.user_personalization.date_night_blender.Path") as mock_path:
        mock_path.return_value = sessions_file
        
        # Simulate UI activation
        initiate_date_night(pack_a, pack_b)
        
        # Verify activation
        assert is_date_night_active()
        assert st.session_state.blended_prefs["moods"]["happy"] == pytest.approx(0.65)
        
        # Verify session log was created
        assert sessions_file.exists()
        
        # Simulate ending
        end_date_night()
        assert not is_date_night_active()

# Error Cases
def test_invalid_pack_combinations(sample_packs):
    """Test error handling for invalid packs"""
    invalid_pack = {"name": "Invalid"}
    
    with pytest.raises(ValueError):
        blend_packs(invalid_pack, sample_packs["romcom"])


# Update test_blend_packs to match your implementation
def test_blend_packs(sample_packs):
    """Test full pack blending"""
    blended = blend_packs(sample_packs["romcom"], sample_packs["action"])
    
    # Verify mood blending
    assert blended["moods"]["happy"] == pytest.approx(0.65)
    assert "excited" in blended["moods"]
    
    # Verify metadata - updated to check for 'combined_at' instead of 'blended_at'
    assert blended["source_packs"] == ["Romantic Comedy", "Action Pack"]
    assert "combined_at" in blended  # Changed from 'blended_at'
    assert "movies" in blended
    assert "preference_weight" in blended


def test_save_date_session(sample_packs, tmp_path):
    """Test session persistence with proper file handling"""
    # Setup test directory
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    sessions_file = session_dir / "date_sessions.json"
    
    # Mock the Path to return our test directory
    with patch("ai_smart_recommender.user_personalization.date_night_blender.Path") as mock_path:
        # When Path() is called with "sessions", return our test directory
        mock_path.return_value = session_dir
        
        # Call the function
        session_id = save_date_session(
            sample_packs["romcom"],
            sample_packs["action"],
            {"moods": {}, "movies": {}}
        )
    
    # Verify the file was created
    assert sessions_file.exists()
    
    # Read and verify contents - using pathlib for better Windows compatibility
    content = sessions_file.read_text(encoding='utf-8')
    sessions = json.loads(content)
    
    assert len(sessions) == 1
    assert sessions[0]["meta"]["session_id"] == session_id
    assert sessions[0]["packs"]["a"]["name"] == "Romantic Comedy"
    assert sessions[0]["system"]["success"] is True

def test_duplicate_packs(sample_packs):
    """Test that blending duplicate packs works"""
    blended = blend_packs(sample_packs["romcom"], sample_packs["romcom"])
    
    # Verify the blended pack contains expected data
    assert blended["source_packs"] == ["Romantic Comedy", "Romantic Comedy"]
    assert blended["moods"]["happy"] == pytest.approx(0.8)  # Should be same as original