import unittest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Mock the Streamlit imports
sys.modules['streamlit'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['requests'] = MagicMock()

# Import the component after mocking
from ui_components.RecommendationCard import RecommendationCard

class TestUIRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load test data
        test_data_path = Path(__file__).parent.parent.parent.parent / 'static_data' / 'test_recommendations.json'
        with open(test_data_path, 'r') as f:
            cls.test_data = json.load(f)
    
    def setUp(self):
        # Create a complete mock recommendation
        self.sample_rec = {
            'id': 550,
            'title': 'Fight Club',
            'similarity_score': 0.92,
            'match_type': 'hybrid',
            'explanation': 'Similar themes of hope and institutional critique',
            'genres': ['Drama'],
            'actors': ['Brad Pitt', 'Edward Norton'],
            'poster_path': '/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg',
            'backdrop_path': '/rr7E0NoGKxvbkb89eR1GwfoYjpA.jpg',
            'vote_average': 8.8,
            'release_year': 1999,
            'release_date': '1999-10-15',
            'vibe': 'Dark, Thought-Provoking',
            'runtime': 139
        }

    def test_recommendation_card_renders_all_elements(self):
        """Test that all UI elements render with correct data"""
        with patch('streamlit.columns') as mock_cols, \
            patch('streamlit.image') as mock_image, \
            patch('streamlit.markdown') as mock_markdown, \
            patch('streamlit.caption') as mock_caption, \
            patch('streamlit.progress') as mock_progress, \
            patch('streamlit.expander') as mock_expander, \
            patch('streamlit.button') as mock_button, \
            patch('streamlit.session_state', new_callable=dict):
            
            # Setup mock columns
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_cols.return_value = (mock_col1, mock_col2)
            
            # make button not click
            mock_button.return_value = False
            
            # Call the component
            RecommendationCard(self.sample_rec)
            
            # Verify poster image
            mock_image.assert_called_once()
            
            # Verify title
            mock_markdown.assert_called_with('**Fight Club**')
            
            # Verify release date caption
            mock_caption.assert_any_call("📅 1999")
            
            # Verify genres
            mock_caption.assert_any_call("🎭 Drama")
            
            # Verify progress bar with correct rating
            called_args, called_kwargs = mock_progress.call_args
            self.assertAlmostEqual(called_args[0], 0.88, places=2)
            self.assertEqual(called_kwargs['text'], "Rating: 8.8/10")
            
            # Explanation toggle default
            mock_expander.assert_called_with("ℹ️ Why this rec?", expanded=False)
            
            # Verify action buttons rendered with correct labels and keys
            mock_button.assert_any_call("View details", key="view_550")
            mock_button.assert_any_call("❤️ Watchlist", key="watchlist_550")


    def test_recommendation_card_explanation_toggle(self):
        """Test that explanation expands when requested"""
        with patch('streamlit.columns') as mock_cols, \
            patch('streamlit.expander') as mock_expander:
            
            mock_cols.return_value = (MagicMock(), MagicMock())
            
            RecommendationCard(self.sample_rec, show_explanation=True)
            mock_expander.assert_called_with("ℹ️ Why this rec?", expanded=True)

    def test_recommendation_card_image_fallback(self):
        """Test that placeholder appears when poster is missing"""
        no_poster_rec = {**self.sample_rec, 'poster_path': None}
        
        with patch('streamlit.columns') as mock_cols, \
            patch('streamlit.image') as mock_image:
            
            # fix: make columns return two mock columns
            mock_cols.return_value = (MagicMock(), MagicMock())
            
            RecommendationCard(no_poster_rec)
            
            mock_image.assert_called_with(
                "media_assets/icons/image-fallback.svg",
                width=120,
                caption="Fight Club"
            )



    def test_recommendation_card_missing_data(self):
        """Test graceful handling of missing optional fields"""
        minimal_rec = {
            'movie_id': 999,
            'title': 'Unknown Movie',
            'similarity_score': 0.5,
            'match_type': 'fallback',
            'explanation': 'Fallback recommendation',
            'genres': []
        }
        
        with patch('streamlit.columns') as mock_cols, \
             patch('streamlit.image') as mock_image:
            
            mock_cols.return_value = (MagicMock(), MagicMock())
            
            # Should not raise exceptions
            RecommendationCard(minimal_rec)
            
            # Should still try to show image (fallback)
            mock_image.assert_called()
            
    def test_watchlist_button_functionality(self):
        """Test that clicking the watchlist button updates session state"""
        with patch('streamlit.columns') as mock_cols, \
            patch('streamlit.button') as mock_button, \
            patch('streamlit.session_state', new_callable=dict) as mock_state, \
            patch('streamlit.toast') as mock_toast:
            
            # Mock columns to avoid unpack error
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_cols.return_value = (mock_col1, mock_col2)
            
            # Initially watchlist is empty
            mock_state['watchlist'] = []
            
            # Simulate button clicks:
            # - first button (View details): not clicked
            # - second button (Watchlist): clicked
            mock_button.side_effect = [False, True]
            
            RecommendationCard(self.sample_rec)
            
            # Check that the movie id was added
            assert 550 in mock_state['watchlist']
            
            # Toast confirmation called
            mock_toast.assert_called_with("Added Fight Club to watchlist")


    def test_recommendations_data_structure(self):
        """Test that the test recommendations data is properly structured"""
        # Verify base movie exists
        self.assertIn('base_movie', self.test_data)
        self.assertIn('title', self.test_data['base_movie'])
        
        # Verify recommendations exist
        self.assertIn('recommendations', self.test_data)
        self.assertGreater(len(self.test_data['recommendations']), 0)
        
        # Check each recommendation has required fields
        required_fields = [
            'movie_id', 'title', 'similarity_score', 
            'match_type', 'explanation', 'genres',
            'poster_path', 'release_date'
        ]
        for rec in self.test_data['recommendations']:
            for field in required_fields:
                self.assertIn(field, rec)

if __name__ == '__main__':
    unittest.main()