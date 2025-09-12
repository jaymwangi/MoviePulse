import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Mock all heavy dependencies before importing anything from the app
mock_modules = {
    'ai_smart_recommender': Mock(),
    'service_clients': Mock(),
    'service_clients.local_store': Mock(),
    'ai_smart_recommender.recommender_engine': Mock(),
    'ai_smart_recommender.recommender_engine.strategy_interfaces': Mock(),
    'ai_smart_recommender.recommender_engine.strategy_interfaces.hybrid_model': Mock(),
    'ai_smart_recommender.interfaces.fallback_rules': Mock(),
    'ui_components.RecommendationCard': Mock(),
    'ui_components.MovieCard': Mock(),
    'ui_components.UserProfile': Mock(),
    'data_models.user_profile': Mock(),
    'data_models.movie_models': Mock(),
    'utils.logging_config': Mock(),
}

# Apply the mocks
for module_name, mock_obj in mock_modules.items():
    sys.modules[module_name] = mock_obj

# Now import the module under test
try:
    from ui_components.SettingsPanel import render_settings_panel, render_quick_settings
    HAS_CREATE_SETTINGS = False
except ImportError:
    # Try importing without create_settings_panel if it doesn't exist
    from ui_components.SettingsPanel import render_settings_panel, render_quick_settings
    HAS_CREATE_SETTINGS = False

class TestSettingsPanel:
    """Test suite for the SettingsPanel component"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mock session state and patches before each test"""
        # Clear and setup session state
        st.session_state.clear()
        st.session_state.update({
            'theme': 'dark',
            'font': 'default',
            'spoiler_free': False,
            'dyslexia_mode': False,
            'critic_mode_pref': 'balanced',
            'user_preferences': {
                'theme': 'dark',
                'font': 'default',
                'spoiler_free': False,
                'dyslexia_mode': False,
                'critic_mode': 'balanced',
                'notifications_enabled': True
            }
        })
        
        # Create all the mock patches
        self.patches = {
            'load_prefs': patch('ui_components.SettingsPanel.load_user_preferences'),
            'get_theme': patch('ui_components.SettingsPanel.get_theme'),
            'get_font': patch('ui_components.SettingsPanel.get_font'),
            'is_spoiler_free': patch('ui_components.SettingsPanel.is_spoiler_free'),
            'is_dyslexia_mode': patch('ui_components.SettingsPanel.is_dyslexia_mode'),
            'get_critic_mode_pref': patch('ui_components.SettingsPanel.get_critic_mode_pref'),
            'handle_settings_change': patch('ui_components.SettingsPanel.handle_settings_change'),
            'save_prefs': patch('ui_components.SettingsPanel.save_user_preferences')
        }
        
        # Start all patches and store references
        self.mocks = {}
        for name, patch_obj in self.patches.items():
            self.mocks[name] = patch_obj.start()
        
        # Setup return values - use values that match your actual CRITIC_MODE_OPTIONS
        self.mocks['load_prefs'].return_value = {
            'theme': 'dark',
            'font': 'default',
            'spoiler_free': False,
            'dyslexia_mode': False,
            'critic_mode': 'standard',  # Changed to match likely options
            'notifications_enabled': True
        }
        self.mocks['get_theme'].return_value = 'dark'
        self.mocks['get_font'].return_value = 'default'
        self.mocks['is_spoiler_free'].return_value = False
        self.mocks['is_dyslexia_mode'].return_value = False
        self.mocks['get_critic_mode_pref'].return_value = 'standard'  # Changed
        self.mocks['save_prefs'].return_value = True
        
        # Mock CRITIC_MODE_OPTIONS to match what your code expects
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']):
            yield
        
        # Clean up all patches
        for patch_obj in self.patches.values():
            patch_obj.stop()
    
    def test_render_settings_panel_structure(self):
        """Test that the settings panel renders all expected sections"""
        # Mock CRITIC_MODE_OPTIONS to avoid the ValueError
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']), \
             patch('streamlit.header'), \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.toggle') as mock_toggle, \
             patch('streamlit.button'), \
             patch('streamlit.info'):
            
            # Mock columns to return proper mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock the expander context manager
            mock_expander_instance = MagicMock()
            mock_expander.return_value.__enter__.return_value = mock_expander_instance
            
            # Mock selectbox returns with proper values
            mock_selectbox.side_effect = ['dark', 'default', 'standard']
            
            # FIX: Use return_value instead of side_effect for toggle to avoid StopIteration
            mock_toggle.return_value = False
            
            render_settings_panel()
            
            # Verify expanders were created
            assert mock_expander.call_count >= 3
    
    def test_theme_selection_change(self):
        """Test that theme changes trigger the handler"""
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']), \
             patch('streamlit.header'), \
             patch('streamlit.expander'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.toggle'), \
             patch('streamlit.button'), \
             patch('streamlit.info'):
            
            # Mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock selectbox to return a different theme
            mock_selectbox.side_effect = ['light', 'default', 'standard']
            
            render_settings_panel()
            
            # Verify handle_settings_change was called with the new theme
            self.mocks['handle_settings_change'].assert_any_call('theme', 'light')
    
    def test_font_selection_change(self):
        """Test that font changes trigger the handler"""
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']), \
             patch('streamlit.header'), \
             patch('streamlit.expander'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.toggle'), \
             patch('streamlit.button'), \
             patch('streamlit.info'):
            
            # Mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock selectbox to return a different font
            mock_selectbox.side_effect = ['dark', 'dyslexia', 'standard']
            
            render_settings_panel()
            
            # Verify handle_settings_change was called with the new font
            self.mocks['handle_settings_change'].assert_any_call('font', 'dyslexia')
    
    def test_accessibility_toggles(self):
        """Test that accessibility toggles work correctly"""
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']), \
             patch('streamlit.header'), \
             patch('streamlit.expander'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox'), \
             patch('streamlit.toggle') as mock_toggle, \
             patch('streamlit.button'), \
             patch('streamlit.info'):
            
            # Mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock toggles to return True (enabled) - use return_value instead of side_effect
            mock_toggle.return_value = True
            
            render_settings_panel()
            
            # Verify toggles were called
            assert mock_toggle.call_count >= 2
    
    def test_render_quick_settings(self):
        """Test the quick settings sidebar component"""
        with patch('streamlit.sidebar.header'), \
             patch('streamlit.sidebar.selectbox') as mock_selectbox, \
             patch('streamlit.sidebar.columns') as mock_columns, \
             patch('streamlit.sidebar.button'), \
             patch('streamlit.sidebar.divider'):
            
            # Mock columns to return proper mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            # Mock selectbox to return a different theme
            mock_selectbox.return_value = 'light'
            
            render_quick_settings()
            
            # Verify handle_settings_change was called
            self.mocks['handle_settings_change'].assert_called_with('theme', 'light')
    
    def test_settings_persistence(self):
        """Test that settings are loaded from persistence"""
        # Setup mock to return different values
        self.mocks['load_prefs'].return_value = {
            'theme': 'light',
            'font': 'dyslexia',
            'spoiler_free': True,
            'dyslexia_mode': True,
            'critic_mode': 'strict',
            'notifications_enabled': False
        }
        
        with patch('ui_components.SettingsPanel.CRITIC_MODE_OPTIONS', ['standard', 'strict', 'lenient']), \
             patch('streamlit.header'), \
             patch('streamlit.expander'), \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.selectbox'), \
             patch('streamlit.toggle'), \
             patch('streamlit.button'), \
             patch('streamlit.info'):
            
            # Mock columns
            mock_col1, mock_col2 = MagicMock(), MagicMock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            render_settings_panel()
            
            # Verify settings were loaded from persistence
            self.mocks['load_prefs'].assert_called_once()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])