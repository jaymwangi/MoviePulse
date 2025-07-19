import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from pathlib import Path
from service_clients import tmdb_client
from ai_smart_recommender.user_personalization.watch_history import WatchHistory

@pytest.fixture
def mock_history_file(tmp_path):
    data = """{"user_id":"u1","movie_id":1,"timestamp":"2023-01-01T00:00:00","genres":["drama"],"source":"organic","log_id":"1"}
{"user_id":"u2","movie_id":2,"timestamp":"2023-01-02T00:00:00","genres":["action"],"source":"organic","log_id":"2"}"""
    file_path = tmp_path / "history.jsonl"
    file_path.write_text(data)
    return file_path

@pytest.fixture
def mock_empty_history_file(tmp_path):
    file_path = tmp_path / "empty_history.jsonl"
    file_path.write_text("")
    return file_path

@pytest.fixture
def mock_affinity_file(tmp_path):
    file_path = tmp_path / "affinity.json"
    file_path.write_text("{}")
    return file_path

@pytest.fixture
def watch_history(mock_history_file, tmp_path):
    """Fixture that provides a WatchHistory instance with mock files"""
    return WatchHistory(
        history_path=mock_history_file,
        affinity_path=tmp_path / "affinity.json"
    )

@pytest.fixture
def empty_watch_history(mock_empty_history_file, tmp_path):
    """Fixture that provides a WatchHistory instance with empty history"""
    return WatchHistory(
        history_path=mock_empty_history_file,
        affinity_path=tmp_path / "affinity.json"
    )

@pytest.fixture
def mock_tmdb_client():
    with patch('ai_smart_recommender.user_personalization.watch_history.tmdb_client') as mock:
        mock_movie = MagicMock()
        mock_genre = MagicMock()
        mock_genre.name = "Drama"
        mock_movie.genres = [mock_genre]
        mock.get_movie_details.return_value = mock_movie
        yield mock

def test_add_entry(watch_history, tmp_path):
    # Clear existing file to start fresh
    watch_history.history_path.write_text("")
    
    # Test adding first entry
    entry = watch_history.add_entry("u3", 3, ["comedy"])
    
    # Verify return value
    assert entry["user_id"] == "u3"
    assert entry["movie_id"] == 3
    assert entry["genres"] == ["comedy"]
    assert entry["source"] == "organic"
    assert "log_id" in entry
    assert "timestamp" in entry
    
    # Verify file was updated
    assert watch_history.history_path.exists()
    with open(watch_history.history_path) as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["movie_id"] == 3

def test_get_user_history(watch_history):
    # Test existing user
    history = watch_history.get_user_history("u1")
    assert len(history) == 1
    assert history[0]["movie_id"] == 1
    
    # Test with limit
    assert len(watch_history.get_user_history("u1", limit=0)) == 0
    
    # Test non-existent user
    assert len(watch_history.get_user_history("u99")) == 0

def test_get_user_history_empty(empty_watch_history):
    assert len(empty_watch_history.get_user_history("u1")) == 0

def test_update_affinity(watch_history):
    # Test affinity calculation
    affinity = watch_history.update_affinity("u1")
    
    assert isinstance(affinity, dict)
    assert "top_genres" in affinity
    assert affinity["top_genres"][0] == "drama"
    assert "genre_counts" in affinity
    assert affinity["genre_counts"]["drama"] == 1
    assert "total_watched" in affinity
    assert affinity["total_watched"] == 1
    assert "last_updated" in affinity
    
    # Verify file content
    with open(watch_history.affinity_path) as f:
        data = json.load(f)
        assert "u1" in data
        assert data["u1"]["top_genres"][0] == "drama"

def test_update_affinity_new_user(empty_watch_history):
    affinity = empty_watch_history.update_affinity("new_user")
    assert isinstance(affinity, dict)
    assert "top_genres" in affinity
    assert isinstance(affinity["top_genres"], list)
    assert len(affinity["top_genres"]) == 0
    assert "genre_counts" in affinity
    assert isinstance(affinity["genre_counts"], dict)
    assert len(affinity["genre_counts"]) == 0
    assert "total_watched" in affinity
    assert affinity["total_watched"] == 0

def test_with_mocked_tmdb(mock_tmdb_client):
    wh = WatchHistory()
    
    # Clear any existing history
    wh.history_path.write_text("")
    
    # Test that TMDB client is called when genres aren't provided
    entry = wh.add_entry("u1", 1)
    
    # Verify TMDB client was called
    mock_tmdb_client.get_movie_details.assert_called_once_with(1)
    
    # Verify history entry
    history = wh.get_user_history("u1")
    assert len(history) == 1
    assert history[0]["genres"][0].lower() == "drama"

def test_affinity_file_creation(tmp_path):
    """Test that affinity file is created with proper structure"""
    wh = WatchHistory(affinity_path=tmp_path/"new_affinity.json")
    assert wh.affinity_path.exists()
    assert json.loads(wh.affinity_path.read_text()) == {}

def test_corrupted_affinity_file(tmp_path):
    """Test handling of corrupted affinity file"""
    bad_file = tmp_path / "bad_affinity.json"
    bad_file.write_text("{invalid}")
    
    # Should handle the corruption gracefully
    wh = WatchHistory(affinity_path=bad_file)
    
    # Verify the file was recreated properly
    assert wh.affinity_path.exists()
    try:
        json.loads(wh.affinity_path.read_text())
    except json.JSONDecodeError:
        pytest.fail("Affinity file still corrupted after initialization")
    
    # Test that we can still update affinity
    affinity = wh.update_affinity("u1")
    assert isinstance(affinity, dict)

def test_multiple_genre_affinity(watch_history):
    """Test affinity calculation with multiple genres"""
    # Clear existing history for clean test
    watch_history.history_path.write_text("")
    
    # Add initial entry
    watch_history.add_entry("u1", 1, ["drama"])
    
    # Add entry with multiple genres
    watch_history.add_entry("u1", 2, ["comedy", "romance"])
    
    # Calculate affinity
    affinity = watch_history.update_affinity("u1")
    
    # Verify results
    assert len(affinity["top_genres"]) <= 3
    assert "comedy" in affinity["genre_counts"]
    assert "romance" in affinity["genre_counts"]
    assert "drama" in affinity["genre_counts"]
    assert affinity["total_watched"] == 2

def test_add_entry_with_source(watch_history):
    # Clear any existing entries for u3
    watch_history.history_path.write_text("")
    
    # Test adding entry with custom source
    entry = watch_history.add_entry("u3", 3, ["comedy"], source="recommendation")
    assert entry["source"] == "recommendation"
    
    # Verify it was saved correctly
    history = watch_history.get_user_history("u3")
    assert len(history) == 1
    assert history[0]["source"] == "recommendation"

def test_get_affinity(tmp_path):
    wh = WatchHistory(affinity_path=tmp_path/"affinity.json")
    
    # Test empty affinity
    assert wh.get_affinity("u1") == {}
    
    # Test with existing affinity
    test_data = {"u1": {"top_genres": ["drama"], "genre_counts": {"drama": 1}, "total_watched": 1}}
    wh.affinity_path.write_text(json.dumps(test_data))
    assert wh.get_affinity("u1")["top_genres"] == ["drama"]

def test_duplicate_entries(watch_history):
    """Test that duplicate entries are handled correctly"""
    # Clear existing history
    watch_history.history_path.write_text("")
    
    # Add same entry twice
    entry1 = watch_history.add_entry("u1", 1, ["drama"])
    entry2 = watch_history.add_entry("u1", 1, ["drama"])
    
    # Both should be recorded with different log_ids
    assert entry1["log_id"] != entry2["log_id"]
    
    # Both should appear in history
    history = watch_history.get_user_history("u1")
    assert len(history) == 2

def test_invalid_movie_id(watch_history, mock_tmdb_client):
    """Test handling of invalid movie IDs"""
    # Setup mock to return a serializable response
    mock_genre = MagicMock()
    mock_genre.name = "unknown"
    mock_movie = MagicMock()
    mock_movie.genres = [mock_genre]
    mock_tmdb_client.get_movie_details.return_value = mock_movie
    
    # Clear any existing history
    watch_history.history_path.write_text("")
    
    # Add entry with invalid ID
    entry = watch_history.add_entry("u1", -1)
    
    # Verify results
    assert entry["genres"] == ["unknown"]
    mock_tmdb_client.get_movie_details.assert_called_once_with(-1)
    
    # Verify the entry was properly saved
    history = watch_history.get_user_history("u1")
    assert len(history) == 1
    assert history[0]["genres"] == ["unknown"]