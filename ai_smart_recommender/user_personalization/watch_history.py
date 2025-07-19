import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import uuid
import logging
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TMDB Client setup with fallback for testing
try:
    from service_clients import tmdb_client
except ImportError:
    logger.warning("TMDB client not found, using mock implementation")
    
    class MockTMDBClient:
        @staticmethod
        def get_movie_details(movie_id: int) -> Any:
            mock_genre = MagicMock()
            mock_genre.name = "Drama"  # Default mock genre
            mock_movie = MagicMock()
            mock_movie.genres = [mock_genre]
            return mock_movie

    tmdb_client = MockTMDBClient()


class WatchHistory:
    """Manages user watch history and genre affinity calculations."""
    
    def __init__(
        self, 
        history_path: Optional[Union[str, Path]] = None, 
        affinity_path: Optional[Union[str, Path]] = None
    ):
        """
        Initialize WatchHistory with file paths.
        
        Args:
            history_path: Path to the watch history JSONL file
            affinity_path: Path to the user affinity JSON file
        """
        # Convert string paths to Path objects if needed
        self.history_path = Path(history_path) if isinstance(history_path, str) else history_path or Path("static_data/watch_history.jsonl")
        self.affinity_path = Path(affinity_path) if isinstance(affinity_path, str) else affinity_path or Path("static_data/user_affinity.json")

        self._initialize_files()

    def _initialize_files(self) -> None:
        """Ensure data files and directories exist with proper permissions."""
        try:
            # Create parent directories if they don't exist
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            self.affinity_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize history file if it doesn't exist
            self.history_path.touch(exist_ok=True)
            
            # Handle affinity file initialization
            if not self.affinity_path.exists():
                self.affinity_path.write_text("{}")
            else:
                try:
                    # Verify file is valid JSON
                    with open(self.affinity_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Affinity file corrupted, recreating: {e}")
                    self.affinity_path.write_text("{}")
                    
        except (IOError, OSError) as e:
            logger.error(f"Failed to initialize data files: {e}")
            raise RuntimeError(f"Could not initialize data files: {e}")

    def add_entry(
        self, 
        user_id: str, 
        movie_id: int, 
        genres: Optional[List[str]] = None,
        source: str = "organic"
    ) -> Dict[str, Any]:
        """
        Add a new entry to the watch history.
        
        Args:
            user_id: Unique user identifier
            movie_id: TMDB movie ID
            genres: List of genre names (fetched from TMDB if None)
            source: How the movie was discovered ('organic', 'recommendation', etc.)
            
        Returns:
            The created entry dictionary
        """
        if genres is None:
            try:
                movie_details = tmdb_client.get_movie_details(movie_id)
                # Handle both real TMDB response and mock objects
                if hasattr(movie_details, 'genres'):
                    genres = [getattr(genre, 'name', 'unknown').lower() 
                             for genre in getattr(movie_details, 'genres', [])]
                else:
                    genres = ["unknown"]
            except Exception as e:
                logger.warning(f"Failed to fetch genres from TMDB for movie {movie_id}: {e}")
                genres = ["unknown"]

        entry = {
            "user_id": user_id,
            "movie_id": movie_id,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "genres": genres,
            "log_id": str(uuid.uuid4())
        }

        try:
            with open(self.history_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            return entry
        except (IOError, OSError) as e:
            logger.error(f"Failed to write history entry: {e}")
            raise RuntimeError(f"Could not write history entry: {e}")

    def get_user_history(
        self, 
        user_id: str, 
        limit: Optional[int] = None,
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve a user's watch history.
        
        Args:
            user_id: User to get history for
            limit: Maximum number of entries to return
            reverse: Return entries in reverse chronological order (newest first)
            
        Returns:
            List of history entries
        """
        history = []
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("user_id") == user_id:
                            history.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON line in history file: {line}. Error: {e}")
                        continue

            # Sort by timestamp (newest first by default)
            history.sort(
                key=lambda x: x.get("timestamp", ""), 
                reverse=reverse
            )
            
            return history[:limit] if limit is not None else history
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to read history file: {e}")
            return []

    def update_affinity(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate and update genre affinity for a user.
        
        Args:
            user_id: User to update affinity for
            
        Returns:
            The updated affinity data
        """
        history = self.get_user_history(user_id)
        affinity = {
            "top_genres": [],
            "genre_counts": {},
            "last_updated": datetime.now().isoformat(),
            "total_watched": len(history)
        }

        if history:
            genre_counts = {}
            for entry in history:
                for genre in entry.get("genres", []):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

            if genre_counts:
                # Get top 3 genres by count
                affinity["top_genres"] = sorted(
                    genre_counts.keys(),
                    key=lambda x: genre_counts[x],
                    reverse=True
                )[:3]
                affinity["genre_counts"] = genre_counts

        try:
            # Read existing affinity data
            all_affinity = {}
            if self.affinity_path.exists():
                try:
                    with open(self.affinity_path, 'r', encoding='utf-8') as f:
                        all_affinity = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Affinity file corrupted, resetting: {e}")
                    all_affinity = {}

            # Update with new affinity data
            all_affinity[user_id] = affinity
            
            # Write back to file
            with open(self.affinity_path, 'w', encoding='utf-8') as f:
                json.dump(all_affinity, f, indent=2, ensure_ascii=False)
                
            return affinity
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to update affinity file: {e}")
            raise RuntimeError(f"Could not update affinity: {e}")

    def get_affinity(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's genre affinity data.
        
        Args:
            user_id: User to get affinity for
            
        Returns:
            The user's affinity data or empty dict if not found
        """
        try:
            if not self.affinity_path.exists():
                return {}

            with open(self.affinity_path, 'r', encoding='utf-8') as f:
                all_affinity = json.load(f)
                return all_affinity.get(user_id, {})
                
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read affinity data: {e}")
            return {}