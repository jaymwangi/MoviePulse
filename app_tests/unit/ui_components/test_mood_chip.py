# app_tests/unit/ui_components/test_mood_chip.py
import pytest
from unittest.mock import patch, mock_open, MagicMock
import json
from pathlib import Path
import streamlit as st

# Import the component to test
from ui_components.MoodChip import (
    MoodManager,
    MoodChip,
    MoodSelector,
    validate_moods,
    clear_mood_selections
)

# Test data
TEST_MOOD_DATA = {
    "Uplifting": {
        "genres": [35, 10751, 10402],
        "weight": 1.2,
        "description": "Feel-good films",
        "conflicts": ["Melancholic"]
    },
    "Melancholic": {
        "genres": [18, 36],
        "weight": 1.0,
        "description": "Bittersweet stories",
        "conflicts": ["Uplifting"]
    }
}

@pytest.fixture
def mock_mood_data():
    """Fixture to mock mood data loading."""
    with patch("ui_components.MoodChip.MoodManager._load_mood_data") as mock_load:
        mock_load.return_value = TEST_MOOD_DATA
        yield mock_load

@pytest.fixture
def mock_streamlit():
    """Fixture to mock Streamlit components."""
    with patch("streamlit.columns") as mock_cols, \
         patch("streamlit.container") as mock_container, \
         patch("streamlit.checkbox") as mock_checkbox, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption") as mock_caption, \
         patch("streamlit.rerun") as mock_rerun, \
         patch("streamlit.session_state", {}) as mock_session:
        
        # Mock columns to return two mock columns
        mock_cols.return_value = [MagicMock(), MagicMock()]
        mock_checkbox.return_value = False  # Default checkbox state
        yield {
            "columns": mock_cols,
            "container": mock_container,
            "checkbox": mock_checkbox,
            "button": mock_button,
            "markdown": mock_markdown,
            "caption": mock_caption,
            "rerun": mock_rerun,
            "session_state": mock_session
        }


@pytest.fixture
def mock_mood_data():
    """Fixture to mock mood data loading."""
    with patch("ui_components.MoodChip.MoodManager._load_mood_data") as mock_load:
        mock_load.return_value = TEST_MOOD_DATA
        yield mock_load

@pytest.fixture
def mock_session_state():
    """Fixture to mock Streamlit session state."""
    return {}

@pytest.fixture
def mock_streamlit():
    """Fixture to mock Streamlit components."""
    with patch("streamlit.columns") as mock_cols, \
         patch("streamlit.container") as mock_container, \
         patch("streamlit.checkbox") as mock_checkbox, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption") as mock_caption, \
         patch("streamlit.rerun") as mock_rerun, \
         patch("streamlit.session_state", {}) as mock_session:
        
        # Mock columns to return two mock columns
        mock_cols.return_value = [MagicMock(), MagicMock()]
        mock_checkbox.return_value = False  # Default checkbox state
        yield {
            "columns": mock_cols,
            "container": mock_container,
            "checkbox": mock_checkbox,
            "button": mock_button,
            "markdown": mock_markdown,
            "caption": mock_caption,
            "rerun": mock_rerun,
            "session_state": mock_session
        }


def test_mood_manager_load_data(mock_mood_data):
    """Test MoodManager correctly loads and caches data."""
    config = MoodManager.get_mood_config()
    
    assert "Uplifting" in config
    assert config["Uplifting"]["emoji"] == "✨"
    assert config["Uplifting"]["color"] == "#FFD700"
    assert config["Melancholic"]["conflicts"] == ["Uplifting"]

def test_mood_manager_fallback_data():
    """Test fallback data when file loading fails."""
    with patch("builtins.open", side_effect=Exception("File error")):
        config = MoodManager.get_mood_config()
        assert "Uplifting" in config  # From fallback data
        assert "Melancholic" in config

def test_mood_manager_get_moods_by_genre(mock_mood_data):
    """Test getting moods by genre ID."""
    assert MoodManager.get_moods_by_genre(35) == ["Uplifting"]
    assert MoodManager.get_moods_by_genre(18) == ["Melancholic"]
    assert MoodManager.get_moods_by_genre(999) == []  # Non-existent genre

def test_validate_moods_decorator(mock_mood_data):
    """Test the mood validation decorator."""
    @validate_moods
    def dummy_func(moods):
        return moods

    # Valid moods should pass
    assert dummy_func(["Uplifting"]) == ["Uplifting"]
    
    # Invalid moods should raise
    with pytest.raises(ValueError, match="Invalid moods"):
        dummy_func(["InvalidMood"])

def test_mood_chip_disabled_state(mock_mood_data, mock_session_state):
    """Test disabled state prevents toggling."""
    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.rerun") as mock_rerun:
        
        MoodChip("Uplifting", key="test_mood", disabled=True)
        mock_rerun.assert_not_called()


def test_clear_mood_selections(mock_mood_data, mock_session_state):
    """Test clearing mood selections."""
    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.rerun") as mock_rerun:
        
        mock_session_state["test_key_selections"] = ["Uplifting"]
        clear_mood_selections("test_key")
        assert "test_key_selections" not in mock_session_state
        mock_rerun.assert_called()

def test_mood_manager_get_compatible_moods(mock_mood_data):
    """Test mood compatibility logic."""
    # No selections - all moods compatible
    assert set(MoodManager.get_compatible_moods([])) == {"Uplifting", "Melancholic"}
    
    # With selection - filter conflicting moods
    # Note: The test data shows Uplifting conflicts with Melancholic, so when
    # Uplifting is selected, only non-conflicting moods should be returned
    compatible = MoodManager.get_compatible_moods(["Uplifting"])
    assert "Melancholic" not in compatible  # Should be filtered out
    assert "Uplifting" in compatible  # Selected mood should still be included

def test_mood_selector_selection_logic(mock_mood_data, mock_session_state, mock_streamlit):
    """Test selection limit and conflict handling."""
    # Configure mock checkbox to toggle selection state
    def checkbox_side_effect(*args, **kwargs):
        key = kwargs.get("key", "")
        if "test_selector" in key:
            return not mock_session_state.get(key.replace("_cb", ""), False)
        return False
    
    mock_streamlit["checkbox"].side_effect = checkbox_side_effect
    
    # Test selection limit
    selections = MoodSelector(
        moods=["Uplifting", "Melancholic"],
        max_selections=1,
        key="test_selector"
    )
    assert len(selections) <= 1
    
    # Test with conflicts
    mock_session_state["test_selector_selections"] = ["Uplifting"]
    compatible = MoodManager.get_compatible_moods(["Uplifting"])
    assert "Melancholic" not in compatible  # Should be filtered due to conflict
    
def test_mood_chip_initialization(mock_mood_data, mock_streamlit):
    """Test MoodChip component initialization."""
    # Test default initialization
    result = MoodChip("Uplifting", key="test_mood")
    assert result is False  # Should be False by default
    
    # Test with default=True
    result = MoodChip("Uplifting", default=True, key="test_mood2")
    assert result is True

def test_mood_chip_click_behavior(mock_mood_data, mock_streamlit):
    """Test MoodChip toggle behavior."""
    # Setup mock checkbox to simulate click
    mock_streamlit["checkbox"].return_value = True
    
    # Test with click
    result = MoodChip("Uplifting", key="test_mood")
    assert result is True
    
    # Verify rerun was called exactly once
    mock_streamlit["rerun"].assert_called_once()

def test_mood_selector_initialization(mock_mood_data):
    """Test MoodSelector initialization."""
    with patch.dict("streamlit.session_state", {}, clear=True):
        # No initial selections
        selections = MoodSelector(
            moods=["Uplifting", "Melancholic"], 
            key="test_selector"
        )
        assert selections == []

    with patch.dict("streamlit.session_state", {"test_selector_selections": ["Uplifting"]}, clear=True):
        selections = MoodSelector(
            moods=["Uplifting", "Melancholic"], 
            key="test_selector"
        )
        assert selections == ["Uplifting"]

def test_mood_chip_colors(mock_mood_data):
    """Test color generation logic."""
    
    # Override _get_mood_color to simulate mood → hex
    MoodManager._get_mood_color = classmethod(lambda cls, mood: {
        "Uplifting": "#FFD700",   # bright gold → black text
        "Melancholic": "#2F4F4F"  # dark slate → white text
    }.get(mood, "#FFFFFF"))

    assert MoodManager._get_text_color("Uplifting") == "#000000"
    assert MoodManager._get_text_color("Melancholic") == "#FFFFFF"

    # Test hover color
    hover = MoodManager._get_hover_color("Uplifting")
    assert hover != "#FFD700"
