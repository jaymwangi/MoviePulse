# app_tests/unit/ui_components/test_movie_grid.py
from unittest.mock import patch, MagicMock
from ui_components.MovieGridView import MovieGridView

class TestMovieGridView:
    @patch("ui_components.MovieGridView.st.columns")
    @patch("ui_components.MovieGridView.st.checkbox")
    @patch("ui_components.MovieTile.MovieTile")  # Mock the actual import path
    def test_mobile_grid_layout(self, mock_movie_tile, mock_checkbox, mock_columns):
        # Setup
        mock_checkbox.return_value = True  # Simulate mobile
        
        # Create mock columns with proper context manager support
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col1.__enter__.return_value = mock_col1
        mock_col2.__enter__.return_value = mock_col2
        mock_columns.return_value = [mock_col1, mock_col2]
        
        # Test data
        test_movies = [{"id": i, "poster_path": f"poster_{i}.jpg", "title": f"Movie {i}"} for i in range(4)]
        
        # Execute with explicit columns=2 to match mobile layout
        MovieGridView(test_movies, columns=2)
        
        # Verify
        mock_columns.assert_called_once_with(2)
        
        # Verify MovieTile was called 4 times
        assert mock_movie_tile.call_count == 4
        
        # Verify movies were passed correctly
        called_movies = [args[0] for args, _ in mock_movie_tile.call_args_list]
        assert called_movies == test_movies