import pytest
import streamlit as st
import time
from unittest.mock import Mock, patch, MagicMock
from ui_components.ToastNotifications import (
    ToastManager, Toast, ToastType, 
    show_success_toast, show_error_toast,
    show_info_toast, show_warning_toast
)

class TestToastNotifications:
    def setup_method(self):
        """Reset session state before each test"""
        # Clear session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                if key in ['toast_queue', 'active_toasts']:
                    del st.session_state[key]
        
        # Ensure session state has the required attributes
        if 'toast_queue' not in st.session_state:
            st.session_state.toast_queue = []
        if 'active_toasts' not in st.session_state:
            st.session_state.active_toasts = {}
        
        # Reset singleton
        ToastManager._instance = None

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_toast_creation(self, mock_analytics):
        """Test that Toast objects are created correctly"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        toast = Toast("Test message", ToastType.INFO, 3000)
        
        assert toast.message == "Test message"
        assert toast.toast_type == ToastType.INFO
        assert toast.duration == 3000
        assert toast.timestamp is not None
        assert toast.id is not None
        assert "toast_" in toast.id

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_singleton_pattern(self, mock_analytics):
        """Test that ToastManager is a singleton"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager1 = ToastManager()
        manager2 = ToastManager()
        
        assert manager1 is manager2

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_show_toast(self, mock_analytics):
        """Test adding a toast to the queue"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager = ToastManager()
        manager.show_toast("Test message", ToastType.SUCCESS, 2000)
        
        assert len(st.session_state.toast_queue) == 1
        toast = st.session_state.toast_queue[0]
        assert toast.message == "Test message"
        assert toast.toast_type == ToastType.SUCCESS
        assert toast.duration == 2000

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_analytics_logging(self, mock_analytics):
        """Test that toast events are logged to analytics"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager = ToastManager()
        manager.show_toast("Test analytics", ToastType.INFO, 3000)
        
        # Verify analytics call
        mock_instance.log_event.assert_called_once()
        call_args = mock_instance.log_event.call_args
        assert call_args[1]['event_type'] == 'toast_shown'
        assert call_args[1]['toast_type'] == 'info'
        assert 'Test analytics' in call_args[1]['message']
        assert call_args[1]['duration'] == 3000

    def test_convenience_functions(self):
        """Test the convenience functions"""
        with patch('ui_components.ToastNotifications.ToastManager') as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            
            show_success_toast("Success!")
            mock_instance.show_toast.assert_called_with("Success!", ToastType.SUCCESS, 3000)
            
            show_error_toast("Error!")
            mock_instance.show_toast.assert_called_with("Error!", ToastType.ERROR, 5000)
            
            show_info_toast("Info!")
            mock_instance.show_toast.assert_called_with("Info!", ToastType.INFO, 3000)
            
            show_warning_toast("Warning!")
            mock_instance.show_toast.assert_called_with("Warning!", ToastType.WARNING, 4000)

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_toast_queue_processing(self, mock_analytics):
        """Test that toasts are moved from queue to active state"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager = ToastManager()
        
        # Add a toast with past timestamp to simulate ready state
        past_time = time.time() - 1
        toast = Toast("Ready toast", ToastType.INFO, 3000, past_time)
        st.session_state.toast_queue = [toast]
        
        manager._process_queue()
        
        assert len(st.session_state.toast_queue) == 0
        assert len(st.session_state.active_toasts) == 1
        assert toast.id in st.session_state.active_toasts

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_toast_cleanup(self, mock_analytics):
        """Test that expired toasts are cleaned up"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager = ToastManager()
        
        # Add an expired toast
        old_time = time.time() - 4  # 4 seconds ago for a 3-second toast
        toast = Toast("Expired toast", ToastType.INFO, 3000, old_time)
        st.session_state.active_toasts = {toast.id: toast}
        
        manager._cleanup_expired_toasts()
        
        assert len(st.session_state.active_toasts) == 0

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_render_toasts_empty(self, mock_analytics):
        """Test rendering when no toasts are present"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        
        manager = ToastManager()
        
        # Should not raise any errors
        manager.render_toasts()

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    @patch('ui_components.ToastNotifications.st.markdown')
    @patch('ui_components.ToastNotifications.st.container')
    def test_render_toasts_with_content(self, mock_container, mock_markdown, mock_analytics):
        """Test rendering toasts with content"""
        mock_analytics_instance = Mock()
        mock_analytics.return_value = mock_analytics_instance
        
        manager = ToastManager()
        
        # Mock the container
        mock_container_instance = Mock()
        mock_container.return_value.__enter__ = Mock(return_value=mock_container_instance)
        mock_container.return_value.__exit__ = Mock(return_value=None)
        
        # Add an active toast
        toast = Toast("Test render", ToastType.SUCCESS, 3000)
        st.session_state.active_toasts = {toast.id: toast}
        
        manager.render_toasts()
        
        # Verify that markdown was called
        assert mock_markdown.call_count >= 1

    @patch('ui_components.ToastNotifications.AnalyticsClient')
    def test_error_handling(self, mock_analytics):
        """Test that errors in analytics don't break the toast system"""
        mock_instance = Mock()
        mock_analytics.return_value = mock_instance
        mock_instance.log_event.side_effect = Exception("Analytics error")
        
        manager = ToastManager()
        
        # Should not raise an exception
        manager.show_toast("Test error handling", ToastType.ERROR, 3000)
        
        # Toast should still be added to queue
        assert len(st.session_state.toast_queue) == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])