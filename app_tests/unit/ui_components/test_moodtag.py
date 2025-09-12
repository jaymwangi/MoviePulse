# app_tests/unit/ui_components/test_moodtag.py

import pytest
import streamlit as st
import sys
import os
from unittest.mock import MagicMock, patch

# Add the app_ui directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../app_ui'))

from app_ui.components.MoodTag import MoodTag

class TestMoodTag:
    """Test suite for MoodTag component"""
    
    def setup_method(self):
        """Setup before each test method"""
        # Clear session state before each test
        st.session_state.clear()
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_basic_rendering(self, mock_markdown):
        """Test basic MoodTag rendering without emoji or tooltip"""
        MoodTag("Action")
        
        # Verify st.markdown was called
        assert mock_markdown.called
        
        # Get the HTML content passed to markdown
        call_args = mock_markdown.call_args[0][0]
        
        # Verify label is present
        assert "Action" in call_args
        # Verify default classes are present
        assert "mood-tag" in call_args
        assert "mood-tag-medium" in call_args
        assert "mood-tag-default" in call_args
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_with_emoji(self, mock_markdown):
        """Test MoodTag rendering with emoji"""
        MoodTag("Action", "💥")
        
        call_args = mock_markdown.call_args[0][0]
        assert "💥" in call_args
        assert "Action" in call_args
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_with_tooltip(self, mock_markdown):
        """Test MoodTag rendering with tooltip"""
        MoodTag("Romance", "❤️", "Feel-good romantic movies")
        
        call_args = mock_markdown.call_args[0][0]
        assert 'title="Feel-good romantic movies"' in call_args
        assert "❤️" in call_args
        assert "Romance" in call_args
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_size_variants(self, mock_markdown):
        """Test MoodTag size variants"""
        # Test small size
        MoodTag("Small", size="small")
        call_args_small = mock_markdown.call_args[0][0]
        assert "mood-tag-small" in call_args_small
        
        # Test large size
        mock_markdown.reset_mock()
        MoodTag("Large", size="large")
        call_args_large = mock_markdown.call_args[0][0]
        assert "mood-tag-large" in call_args_large
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_style_variants(self, mock_markdown):
        """Test MoodTag style variants"""
        # Test outline variant
        MoodTag("Outline", variant="outline")
        call_args_outline = mock_markdown.call_args[0][0]
        assert "mood-tag-outline" in call_args_outline
        
        # Test solid variant
        mock_markdown.reset_mock()
        MoodTag("Solid", variant="solid")
        call_args_solid = mock_markdown.call_args[0][0]
        assert "mood-tag-solid" in call_args_solid
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_interactive_non_selected(self, mock_markdown):
        """Test interactive MoodTag in non-selected state"""
        result = MoodTag("Interactive", interactive=True, selected=False, key="test_tag")
        
        call_args = mock_markdown.call_args[0][0]
        assert "mood-tag-interactive" in call_args
        assert "mood-tag-selected" not in call_args
        assert result is False  # Should return current state
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_interactive_selected(self, mock_markdown):
        """Test interactive MoodTag in selected state"""
        result = MoodTag("Interactive", interactive=True, selected=True, key="test_tag_selected")
        
        call_args = mock_markdown.call_args[0][0]
        assert "mood-tag-interactive" in call_args
        assert "mood-tag-selected" in call_args
        assert result is True  # Should return current state
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_session_state_management(self, mock_markdown):
        """Test that MoodTag properly manages session state"""
        # First call - should initialize session state to False
        result1 = MoodTag("Test", interactive=True, selected=False, key="state_test")
        assert result1 is False
        
        # Second call with different selected state - should update session state
        result2 = MoodTag("Test", interactive=True, selected=True, key="state_test")
        assert result2 is True
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_non_interactive_no_key(self, mock_markdown):
        """Test that non-interactive tags don't require or use keys"""
        # This should not raise an exception
        result = MoodTag("Non-interactive", interactive=False)
        assert result is None  # Non-interactive tags return None
    
    @patch('app_ui.components.MoodTag.st.markdown')
    def test_moodtag_all_parameters(self, mock_markdown):
        """Test MoodTag with all parameters specified"""
        result = MoodTag(
            label="Drama",
            emoji="🎭",
            tooltip="Serious emotional stories",
            size="large",
            variant="solid",
            interactive=True,
            selected=True,
            key="complete_test"
        )
        
        call_args = mock_markdown.call_args[0][0]
        # Verify all components are present
        assert "Drama" in call_args
        assert "🎭" in call_args
        assert 'title="Serious emotional stories"' in call_args
        assert "mood-tag-large" in call_args
        assert "mood-tag-solid" in call_args
        assert "mood-tag-interactive" in call_args
        assert "mood-tag-selected" in call_args
        assert result is True
