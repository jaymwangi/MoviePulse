import pytest
from unittest.mock import patch, mock_open
import json
from pathlib import Path
from ai_smart_recommender.user_personalization.genre_affinity import GenreAffinityModel


@pytest.fixture
def mock_genres_file(tmp_path):
    """Fixture providing mock genre mappings"""
    data = [
        {"id": 1, "name": "Drama"},
        {"id": 2, "name": "Action"},
        {"id": 3, "name": "Thriller"}
    ]
    file_path = tmp_path / "genres.json"
    file_path.write_text(json.dumps(data))
    return file_path


@pytest.fixture
def mock_affinity_file(tmp_path):
    """Fixture providing mock user affinity data"""
    data = {
        "u1": {
            "view_history": [
                {"genres": ["Drama", "Thriller"]},
                {"genres": ["Drama"]}
            ]
        },
        "empty_user": {
            "view_history": []
        }
    }
    file_path = tmp_path / "affinity.json"
    file_path.write_text(json.dumps(data))
    return file_path


def test_build_preference_vector(mock_genres_file, mock_affinity_file):
    """Test building preference vector with valid data"""
    model = GenreAffinityModel(
        affinity_path=mock_affinity_file,
        genres_path=mock_genres_file
    )
    vector = model.build_preference_vector("u1")
    
    # Verify all expected genres are present
    assert set(vector.keys()) == {"drama", "action", "thriller"}
    
    # Verify specific values
    assert vector["drama"] == pytest.approx(0.67)  # 2/3 occurrences
    assert vector["thriller"] == pytest.approx(0.33)  # 1/3 occurrences
    assert vector["action"] == pytest.approx(0.0)  # Never appeared
    
    # Verify sum of non-zero affinities
    assert sum(v for v in vector.values() if v > 0) == pytest.approx(1.0)


def test_get_top_genres(mock_genres_file, mock_affinity_file):
    """Test getting top genres from preference vector"""
    model = GenreAffinityModel(
        affinity_path=mock_affinity_file,
        genres_path=mock_genres_file
    )
    top_genres = model.get_top_genres("u1", n=2)
    
    assert len(top_genres) == 2
    assert top_genres[0] == "drama"
    assert top_genres[1] == "thriller"


def test_empty_history(mock_genres_file, mock_affinity_file):
    """Test with user having empty view history"""
    model = GenreAffinityModel(
        affinity_path=mock_affinity_file,
        genres_path=mock_genres_file
    )
    vector = model.build_preference_vector("empty_user")
    
    # Should return all genres with 0 affinity
    assert len(vector) == 3  # drama, action, thriller
    assert vector["drama"] == 0.0
    assert vector["action"] == 0.0
    assert vector["thriller"] == 0.0
    assert sum(vector.values()) == 0.0


def test_with_mocked_genres():
    """Test with mocked genre mappings"""
    with patch.object(GenreAffinityModel, '_load_genre_mappings') as mock_load:
        mock_load.return_value = ["drama", "thriller"]
        
        mock_data = {
            "u1": {
                "view_history": [{"genres": ["Drama"]}]
            }
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))), \
             patch.object(Path, 'exists', return_value=True):
            
            model = GenreAffinityModel()
            vector = model.build_preference_vector("u1")
            
            assert set(vector.keys()) == {"drama", "thriller"}
            assert vector["drama"] == pytest.approx(1.0)
            assert vector["thriller"] == pytest.approx(0.0)


def test_missing_files():
    """Test handling of missing data files"""
    # Mock the expected genre list
    mock_genres = ["drama", "action", "thriller"]
    
    with patch.object(GenreAffinityModel, '_load_genre_mappings') as mock_load:
        mock_load.return_value = mock_genres
        
        # Test when both files are missing
        with patch.object(Path, 'exists', return_value=False):
            model = GenreAffinityModel()
            vector = model.build_preference_vector("any_user")
            assert set(vector.keys()) == set(mock_genres)
            assert all(v == 0.0 for v in vector.values())


def test_invalid_json_files():
    """Test handling of invalid JSON data"""
    with patch("builtins.open", mock_open(read_data="invalid json")), \
         patch.object(Path, 'exists', return_value=True):
        
        model = GenreAffinityModel()
        vector = model.build_preference_vector("any_user")
        assert vector == {}


def test_partial_data():
    """Test with partial/malformed data"""
    # Mock the expected genre list
    mock_genres = ["drama", "action"]
    
    with patch.object(GenreAffinityModel, '_load_genre_mappings') as mock_load:
        mock_load.return_value = mock_genres
        
        malformed_data = {
            "u1": {
                "view_history": [
                    {"genres": ["Drama"]},
                    {}  # Missing genres
                ]
            }
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(malformed_data))), \
             patch.object(Path, 'exists', return_value=True):
            
            model = GenreAffinityModel()
            vector = model.build_preference_vector("u1")
            assert "drama" in vector
            assert vector["drama"] == pytest.approx(1.0)
            assert "action" in vector
            assert vector["action"] == 0.0
            assert sum(v for v in vector.values() if v > 0) == pytest.approx(1.0)