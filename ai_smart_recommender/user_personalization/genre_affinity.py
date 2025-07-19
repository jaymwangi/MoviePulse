import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import logging
from core_config.constants import USER_PREFS_LOG_FORMAT

class GenreAffinityModel:
    def __init__(self, affinity_path=None, genres_path=None):
        self.affinity_path = Path(affinity_path) if affinity_path else Path("static_data/user_affinity.json")
        self.genres_path = Path(genres_path) if genres_path else Path("static_data/genres.json")
        self.genre_list = []
        
        # Configure logging
        self.logger = logging.getLogger("user_prefs")
        self.logger.setLevel(logging.INFO)
        
        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            file_handler = logging.FileHandler("logs/user_prefs.log")
            formatter = logging.Formatter(USER_PREFS_LOG_FORMAT)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _load_genre_mappings(self) -> List[str]:
        """Loads genre mappings from file"""
        try:
            if not self.genres_path.exists():
                return []
                
            with open(self.genres_path) as f:
                genres_data = json.load(f)
                if isinstance(genres_data, list):
                    return [g["name"].lower() for g in genres_data]
                return []
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def build_preference_vector(self, user_id: str) -> Dict[str, float]:
        """Builds genre preference vector"""
        self.genre_list = self._load_genre_mappings()
        if not self.genre_list:
            return {}
            
        try:
            if not self.affinity_path.exists():
                return {genre: 0.0 for genre in self.genre_list}
                
            with open(self.affinity_path) as f:
                affinity_data = json.load(f)
        except json.JSONDecodeError:
            return {genre: 0.0 for genre in self.genre_list}
            
        user_data = affinity_data.get(user_id, {})
        history = user_data.get("view_history", [])
        
        genre_counts = defaultdict(int)
        total_views = 0
        
        for entry in history:
            for genre in entry.get("genres", []):
                genre_lower = genre.lower()
                if genre_lower in self.genre_list:
                    genre_counts[genre_lower] += 1
                    total_views += 1
        
        preference_vector = {}
        if total_views > 0:
            for genre in self.genre_list:
                preference_vector[genre] = round(genre_counts.get(genre, 0) / total_views, 2)
        else:
            preference_vector = {genre: 0.0 for genre in self.genre_list}
        
        final_vector = self._apply_decay(preference_vector)
        
        if final_vector:
            top_genres = sorted(final_vector.items(), key=lambda x: x[1], reverse=True)[:3]
            self.logger.info(
                "Affinity updated",
                extra={
                    'user_id': user_id,
                    'genres': [g[0] for g in top_genres],
                    'strength': sum(final_vector.values()),
                    'source': 'history'
                }
            )
        
        return final_vector

    def _apply_decay(self, vector: Dict[str, float]) -> Dict[str, float]:
        """Applies temporal decay to preferences"""
        return vector

    def get_top_genres(self, user_id: str, n: int = 3) -> List[str]:
        """Gets top n preferred genres"""
        vector = self.build_preference_vector(user_id)
        return sorted(vector.keys(), key=lambda x: vector[x], reverse=True)[:n]