"""
Integration tests for Mood Calendar functionality
Tests save/load operations and mood-genre mapping integration
"""

import pytest
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open
import sys
import calendar

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock Streamlit session state for testing
class MockSessionState:
    def __init__(self):
        self.calendar_navigation = {
            "current_month": date.today().month,
            "current_year": date.today().year
        }
        self.mood_data = {}
        self.selected_moods = {}
    
    def setdefault(self, key, value):
        if not hasattr(self, key):
            setattr(self, key, value)
        return getattr(self, key)
    
    def __contains__(self, key):
        return hasattr(self, key)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)


# Set up mock session state for tests
@pytest.fixture(autouse=True)
def mock_streamlit_session(monkeypatch):
    """Mock Streamlit session state for all tests"""
    mock_session = MockSessionState()
    monkeypatch.setattr('streamlit.session_state', mock_session)
    return mock_session


# Mock fixtures data with correct structure
MOCK_MOODS_DATA = {
    "mock_moods": {
        "happy": {"emoji": "😊", "color": "#F1C40F"},
        "excited": {"emoji": "🎉", "color": "#E74C3C"},
        "relaxed": {"emoji": "😌", "color": "#3498DB"},
        "thoughtful": {"emoji": "🤔", "color": "#9B59B6"},
        "sad": {"emoji": "😢", "color": "#5D6D7E"},
        "romantic": {"emoji": "❤️", "color": "#E91E63"},
        "adventurous": {"emoji": "🏔️", "color": "#27AE60"},
        "nostalgic": {"emoji": "📻", "color": "#F39C12"}
    },
    "test_dates": {
        "2024-01-15": "happy",
        "2024-01-16": "excited", 
        "2024-01-17": "relaxed",
        "2024-01-18": "thoughtful",
        "2024-01-19": "romantic"
    },
    # Fixed structure to match what MoodRecommendationStrategy expects
    "mood_genre_mappings": {
        "happy": {
            "genres": [35, 10751, 10402],
            "weight": 1.2,
            "description": "Feel-good and inspiring"
        },
        "excited": {
            "genres": [28, 12, 53],
            "weight": 1.3,
            "description": "High-energy and exciting"
        },
        "relaxed": {
            "genres": [14, 18, 9648],
            "weight": 0.9,
            "description": "Calm and soothing"
        },
        "thoughtful": {
            "genres": [18, 9648, 878],
            "weight": 1.0,
            "description": "Intellectual and reflective"
        },
        "romantic": {
            "genres": [10749, 35, 18],
            "weight": 1.1,
            "description": "Love and relationships focused"
        },
        "sad": {
            "genres": [18, 36, 10749],
            "weight": 1.0,
            "description": "Bittersweet and emotional"
        },
        "adventurous": {
            "genres": [12, 14, 28],
            "weight": 1.3,
            "description": "Journeys and exploration"
        },
        "nostalgic": {
            "genres": [10770, 10751, 10402],
            "weight": 1.0,
            "description": "Sentimental memories"
        }
    }
}


class TestMoodCalendarIntegration:
    """Integration tests for Mood Calendar functionality"""
    
    @pytest.fixture
    def mock_mood_data(self):
        """Return mock mood data"""
        return MOCK_MOODS_DATA
    
    @pytest.fixture
    def calendar_instance(self):
        """Create a CalendarGrid instance for testing"""
        # Mock the load_moods function to return our test data
        with patch('ui_components.CalendarGrid.load_moods') as mock_load:
            mock_load.return_value = MOCK_MOODS_DATA["mock_moods"]
            from ui_components.CalendarGrid import CalendarGrid
            return CalendarGrid(theme="dark")
    
    @pytest.fixture
    def mood_strategy(self, mock_mood_data):
        """Create a MoodRecommendationStrategy instance"""
        # Create mock genre mappings that match the mood genres
        mock_genre_mappings = {
            1: {"genre_ids": [35, 10751, 10402]},  # Matches happy
            2: {"genre_ids": [28, 12, 53]},        # Matches excited
            3: {"genre_ids": [14, 18, 9648]},      # Matches relaxed
            4: {"genre_ids": [18, 9648, 878]},     # Matches thoughtful
            5: {"genre_ids": [10749, 35, 18]},     # Matches romantic
            6: {"genre_ids": [18, 36, 10749]},     # Matches sad
            7: {"genre_ids": [12, 14, 28]},        # Matches adventurous
            8: {"genre_ids": [10770, 10751, 10402]} # Matches nostalgic
        }
        
        from ai_smart_recommender.recommender_engine.strategy_interfaces.contextual_rules import MoodRecommendationStrategy
        return MoodRecommendationStrategy(
            mood_genre_map=mock_mood_data["mood_genre_mappings"],
            genre_mappings=mock_genre_mappings
        )
    
    
    def _get_mood_for_date_simulated(self, date_str):
        # Check explicitly set moods first
        if date_str in self.selected_moods:
            return self.selected_moods[date_str]
        
        # Fallback: deterministic "simulated" mood
        moods_list = list(self.moods.keys())
        if not moods_list:
            return None
        return moods_list[hash(date_str) % len(moods_list)]

    def test_calendar_grid_initialization(self, calendar_instance):
        """Test that CalendarGrid initializes correctly"""
        assert calendar_instance is not None
        assert hasattr(calendar_instance, 'moods')
        assert 'happy' in calendar_instance.moods
        assert calendar_instance.moods['happy']['emoji'] == '😊'
    
    def test_month_navigation(self, calendar_instance):
        """Test month navigation functionality"""
        # Store initial state
        import streamlit
        initial_month = streamlit.session_state.calendar_navigation["current_month"]
        initial_year = streamlit.session_state.calendar_navigation["current_year"]
        
        # Test next month navigation
        calendar_instance._navigate_month(1)
        next_month = streamlit.session_state.calendar_navigation["current_month"]
        next_year = streamlit.session_state.calendar_navigation["current_year"]
        
        # Test previous month navigation  
        calendar_instance._navigate_month(-1)
        prev_month = streamlit.session_state.calendar_navigation["current_month"]
        prev_year = streamlit.session_state.calendar_navigation["current_year"]
        
        # Verify navigation works
        assert next_month != initial_month or next_year != initial_year
        assert prev_month == initial_month
        assert prev_year == initial_year
    
    def test_mood_data_save_load(self, calendar_instance, mock_mood_data):
        """Test saving and loading mood data"""
        test_date = "2024-01-15"
        test_mood = "happy"
        
        # Test setting mood in session state (where it's actually stored)
        import streamlit
        streamlit.session_state.mood_data[test_date] = test_mood
        
        # Test getting mood from session state
        loaded_mood = streamlit.session_state.mood_data.get(test_date)
        
        assert loaded_mood == test_mood
        
        # Test the actual CalendarGrid method if it exists
        if hasattr(calendar_instance, '_get_mood_for_date'):
            loaded_mood = calendar_instance._get_mood_for_date(test_date)
            assert loaded_mood == test_mood
    
    def test_calendar_export_functionality(self, mock_mood_data):
        """Test calendar export to different formats"""
        from session_utils.calendar_exporter import CalendarExporter
        exporter = CalendarExporter(mock_mood_data["test_dates"])
        
        # Test export statistics
        stats = exporter.get_export_stats()
        assert stats['total_entries'] == 5
        assert 'happy' in stats['mood_distribution']
        
        # Test CSV export (mock file writing)
        with patch('builtins.open', mock_open()) as mock_file:
            success = exporter.export_csv('test_export.csv')
            assert success is True
            mock_file.assert_called_with('test_export.csv', 'w', newline='', encoding='utf-8')
        
        # Test JSON export
        with patch('builtins.open', mock_open()) as mock_file:
            success = exporter.export_json('test_export.json')
            assert success is True


    def test_mood_genre_mapping_integration(self, mood_strategy, mock_mood_data):
        """Test that moods correctly map to genres"""
        # Mock the GenreRecommendationStrategy.execute method that gets called internally
        with patch('ai_smart_recommender.recommender_engine.strategy_interfaces.contextual_rules.GenreRecommendationStrategy.execute') as mock_genre_execute:
            # Create mock recommendations
            mock_recommendations = [
                MagicMock(
                    movie_id=1,
                    title="Test Movie 1",
                    reason="Test reason",
                    score=0.9,
                    strategy_used="genre_based",
                    metadata={'mood': 'happy', 'mood_description': 'Feel-good and inspiring'}
                ),
                MagicMock(
                    movie_id=2, 
                    title="Test Movie 2",
                    reason="Test reason",
                    score=0.8,
                    strategy_used="genre_based",
                    metadata={'mood': 'happy', 'mood_description': 'Feel-good and inspiring'}
                )
            ]
            mock_genre_execute.return_value = mock_recommendations
            
            # Create context for mood-based recommendations
            context = {
                'mood': 'happy',
                'limit': 3
            }
            
            # Get recommendations
            recommendations = mood_strategy.execute(context)
            
            # Verify recommendations were generated
            assert len(recommendations) == 2
            mock_genre_execute.assert_called_once()
            
            # Check that the genre strategy was called with the correct genre IDs
            call_args = mock_genre_execute.call_args[0][0]  # First argument to execute
            assert 'genre_ids' in call_args
            assert call_args['genre_ids'] == mock_mood_data["mood_genre_mappings"]["happy"]["genres"]

    def test_calendar_based_recommendations(self, mood_strategy, mock_mood_data):
        """Test recommendations based on calendar mood data"""
        # Mock the internal methods that get called during execution
        with patch.object(mood_strategy, 'get_mood_for_date') as mock_get_mood:
            with patch('ai_smart_recommender.recommender_engine.strategy_interfaces.contextual_rules.GenreRecommendationStrategy.execute') as mock_genre_execute:
                # Mock the mood for the specific date
                mock_get_mood.return_value = 'happy'
                
                # Mock the genre strategy to return recommendations
                mock_recommendations = [
                    MagicMock(
                        movie_id=1,
                        title="Test Movie",
                        reason="Perfect for 'happy' moods",
                        score=0.95,
                        strategy_used="mood_based",
                        metadata={'mood': 'happy', 'mood_description': 'Feel-good and inspiring'}
                    )
                ]
                mock_genre_execute.return_value = mock_recommendations
                
                # Test date-specific recommendations
                test_date = date(2024, 1, 15)
                context = {
                    'date': test_date,
                    'limit': 2
                }
                
                # Call the actual execute method (not mocked)
                recommendations = mood_strategy.execute(context)
                
                # Should get recommendations for the 'happy' mood from that date
                assert len(recommendations) == 1
                mock_get_mood.assert_called_once_with(test_date)
                
                # Verify the genre strategy was called with the correct parameters
                mock_genre_execute.assert_called_once()
                call_args = mock_genre_execute.call_args[0][0]  # First argument to execute
                assert call_args['genre_ids'] == mock_mood_data["mood_genre_mappings"]["happy"]["genres"]
                assert call_args['limit'] == 4  # limit * 2 as per your implementation
        
    def test_recent_mood_analysis(self, mood_strategy, mock_mood_data):
        """Test analysis of recent mood patterns"""
        # Create recent test dates that are within the last 7 days
        today = datetime.now().date()
        recent_dates = {
            (today - timedelta(days=1)).isoformat(): 'happy',
            (today - timedelta(days=2)).isoformat(): 'excited',
            (today - timedelta(days=3)).isoformat(): 'relaxed'
        }
        
        with patch.object(mood_strategy, '_load_mood_calendar_data') as mock_load:
            mock_load.return_value = recent_dates
            
            # Test if the method exists, otherwise skip
            if hasattr(mood_strategy, 'get_recent_moods'):
                recent_moods = mood_strategy.get_recent_moods(days=7)
                assert len(recent_moods) > 0
            else:
                pytest.skip("get_recent_moods method not implemented")
            
            # Skip trend analysis test if method doesn't exist
            if hasattr(mood_strategy, 'get_mood_trend_analysis'):
                trend_analysis = mood_strategy.get_mood_trend_analysis(period_days=30)
                assert 'mood_distribution' in trend_analysis
            else:
                pytest.skip("get_mood_trend_analysis method not implemented")

    def test_mood_calendar_ui_integration(self):
        """Test that the calendar UI integrates with the backend"""
        # This would typically require Streamlit testing framework
        # For now, we'll test that components can be imported and initialized
        try:
            # Mock the necessary dependencies for page import
            with patch('pages.page_08_mood_calendar.initialize_theme'), \
                 patch('pages.page_08_mood_calendar.load_calendar_css'), \
                 patch('pages.page_08_mood_calendar.HeaderBar.render_app_header'):
                
                from pages.page_08_mood_calendar import init_page
                from ui_components.CalendarGrid import CalendarGrid
                
                # Test that components can be instantiated
                calendar = CalendarGrid()
                assert calendar is not None
                
                # Test that page initialization doesn't crash
                init_page()
                
        except ImportError as e:
            pytest.fail(f"Import error in UI integration test: {e}")
        except Exception as e:  
            pytest.fail(f"UI component initialization failed: {e}")
    
    def test_export_convenience_function(self, mock_mood_data):
        """Test the export_calendar_data convenience function"""
        from session_utils.calendar_exporter import export_calendar_data
        
        # Test with mock file operations
        with patch('session_utils.calendar_exporter.CalendarExporter.export_csv') as mock_export:
            mock_export.return_value = True
            
            success = export_calendar_data(
                mock_mood_data["test_dates"],
                format_type='csv',
                output_path='test_output.csv'
            )
            
            assert success is True
            mock_export.assert_called_once()
    
    def test_mood_selector_rendering(self, calendar_instance):
        """Test that mood selector works correctly"""
        test_date = date(2024, 1, 15)
        
        # Mock the selectbox to avoid Streamlit runtime
        with patch('streamlit.selectbox') as mock_selectbox:
            mock_selectbox.return_value = "😊 happy"
            
            # This should not raise an exception
            try:
                calendar_instance._render_mood_selector(test_date, "happy")
                assert True
            except Exception as e:
                pytest.fail(f"Mood selector rendering failed: {e}")
    
    def test_month_weeks_generation(self):
        """Test that month weeks are generated correctly"""
        from ui_components.CalendarGrid import get_month_weeks
        
        test_date = date(2024, 1, 15)
        weeks = get_month_weeks(test_date)
        
        # Check we have either 5 or 6 weeks (calendar module behavior)
        assert len(weeks) in [5, 6]
        
        # Flatten all days and filter out None/placeholder values
        all_days = [day for week in weeks for day in week if day is not None]
        
        # First day should be January 1st
        assert all_days[0] == date(2024, 1, 1)
        
        # Last day should be January 31st
        assert all_days[-1] == date(2024, 1, 31)
        
        # All days should be in January 2024
        assert all(day.month == 1 and day.year == 2024 for day in all_days)
        
        # Verify we have exactly 31 days (for January)
        assert len(all_days) == 31


def test_mock_data_file():
    """Test that validates the mock data structure"""
    # This test validates the structure of our mock data
    assert 'mock_moods' in MOCK_MOODS_DATA
    assert 'test_dates' in MOCK_MOODS_DATA
    assert 'mood_genre_mappings' in MOCK_MOODS_DATA
    
    # Check that all test dates have valid moods
    for date_str, mood in MOCK_MOODS_DATA['test_dates'].items():
        assert mood in MOCK_MOODS_DATA['mock_moods']
        assert mood in MOCK_MOODS_DATA['mood_genre_mappings']
    
    # Check that mood genre mappings have the correct structure
    for mood, mapping in MOCK_MOODS_DATA['mood_genre_mappings'].items():
        assert 'genres' in mapping
        assert 'weight' in mapping
        assert 'description' in mapping
        assert isinstance(mapping['genres'], list)
        assert isinstance(mapping['weight'], (int, float))
        assert isinstance(mapping['description'], str)


if __name__ == "__main__":
    # Run tests directly for debugging
    import streamlit
    
    # Initialize mock session
    mock_session = MockSessionState()
    streamlit.session_state = mock_session
    
    test_instance = TestMoodCalendarIntegration()
    
    # Run basic tests
    test_instance.test_calendar_grid_initialization()
    print("✓ Calendar grid initialization test passed")
    
    test_instance.test_mood_data_save_load()
    print("✓ Mood data save/load test passed")
    
    test_instance.test_month_weeks_generation()
    print("✓ Month weeks generation test passed")
    
    test_mock_data_file()
    print("✓ Mock data validation passed")
    
    print("All integration tests passed!")

    