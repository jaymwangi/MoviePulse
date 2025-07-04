from unittest.mock import patch
from streamlit_pages.1_Home import render

class TestUIRequirements:
    @patch("streamlit_pages.1_Home.st")
    def test_complete_flow(self, mock_st):
        # Test mobile layout
        mock_st.checkbox.return_value = True
        render()
        assert "columns(2)" in str(mock_st.method_calls)
        
        # Test URL param
        mock_st.query_params.get.return_value = "Inception"
        render()
        assert "Inception" in str(mock_st.text_input.call_args)
        
        # Test hover classes exist
        assert "hover:" in str(mock_st.markdown.call_args_list)
        
        # Test loading states
        assert "spinner" in str(mock_st.method_calls)
