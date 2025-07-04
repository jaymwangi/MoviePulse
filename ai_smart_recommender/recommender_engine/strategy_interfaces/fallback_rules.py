"""
Fallback Recommendation Rules Engine

Provides backup recommendation strategies when primary methods in hybrid_model.py fail.
Implements genre and mood compatibility rules with configurable weights and robust error handling.

Key Features:
- Genre compatibility mappings with empty list protection
- Mood-to-genre relationships with defaults
- Similarity matrix for hybrid recommendations
- Validation rules for recommendation consistency
- Comprehensive error handling and logging

This module is designed to work closely with hybrid_model.py's EnhancedHybridRecommender.
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging
from pydantic import BaseModel, field_validator
import numpy as np

logger = logging.getLogger(__name__)

# --------------------------
# Data Models
# --------------------------
class Genre(BaseModel):
    id: int
    name: str

class Mood(BaseModel):
    id: int
    name: str
    description: str

class GenreCompatibilityRule(BaseModel):
    genre_id: int
    compatible_genres: List[int]
    compatible_moods: List[int]
    weight: float = 1.0

    @field_validator('compatible_genres', 'compatible_moods')
    def check_empty_list(cls, v):
        if not v:
            logger.warning("Empty compatibility list detected, using default values")
            return [1]  # Default to some genre/mood
        return v

class MoodCompatibilityRule(BaseModel):
    name: str = "MoodCompatibility"
    mood_id: int
    compatible_genres: List[int]
    compatible_moods: List[int]
    weight: float = 1.0

    @field_validator('compatible_genres', 'compatible_moods')
    def check_empty_list(cls, v):
        if not v:
            logger.warning("Empty compatibility list detected, using default values")
            return [1]  # Default to some genre/mood
        return v

# --------------------------
# Fallback Rules Engine
# --------------------------
class FallbackRules:
    def __init__(self):
        self.genres: Dict[int, GenreCompatibilityRule] = {}
        self.moods: Dict[int, MoodCompatibilityRule] = {}
        self._mood_to_genres: Dict[int, List[int]] = {}
        self._genre_similarity_matrix: Optional[np.ndarray] = None
        self._default_recommendations: List[int] = [1, 2, 3]  # Default popular items

    def load_all(self, genres_file: Path, moods_file: Path) -> bool:
        """Load and validate both files with comprehensive error handling"""
        logger.info(f"Loading fallback rules from {genres_file} and {moods_file}")
        try:
            success = (
                self._load_genres(genres_file) 
                and self._load_moods(moods_file)
                and self._build_compatibility_rules()
            )
            if not success:
                logger.error("Failed to load some rule components, initializing with defaults")
                self._initialize_defaults()
            return success
        except Exception as e:
            logger.error(f"Critical error during rule loading: {str(e)}")
            self._initialize_defaults()
            return False

    def _initialize_defaults(self):
        """Initialize with safe default values when loading fails"""
        self.genres = {
            1: GenreCompatibilityRule(
                genre_id=1,
                compatible_genres=[2, 3],
                compatible_moods=[1, 2]
            )
        }
        self.moods = {
            1: MoodCompatibilityRule(
                mood_id=1,
                compatible_genres=[1, 2],
                compatible_moods=[2, 3]
            )
        }
        self._build_compatibility_rules()

    def _load_genres(self, file_path: Path) -> bool:
        """Load genre rules with validation and empty list protection"""
        try:
            logger.debug(f"Attempting to load genres from {file_path}")
            with open(file_path, 'r') as f:
                genres_data = json.load(f)
            
            self.genres = {}
            for genre in genres_data:
                # Ensure compatible lists are never empty
                compatible_genres = genre.get("compatible_genres", [1])
                compatible_moods = genre.get("compatible_moods", [1])
                
                self.genres[genre["id"]] = GenreCompatibilityRule(
                    genre_id=genre["id"],
                    compatible_genres=compatible_genres or [1],
                    compatible_moods=compatible_moods or [1]
                )
            logger.info(f"Loaded {len(self.genres)} genres successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load genres from {file_path}: {str(e)}")
            return False

    def _load_moods(self, file_path: Path) -> bool:
        """Load mood rules with validation and empty list protection"""
        try:
            logger.debug(f"Attempting to load moods from {file_path}")
            with open(file_path, 'r') as f:
                moods_data = json.load(f)
            
            self.moods = {}
            for mood in moods_data:
                # Ensure compatible lists are never empty
                compatible_genres = mood.get("compatible_genres", [1])
                compatible_moods = mood.get("compatible_moods", [1])
                
                self.moods[mood["id"]] = MoodCompatibilityRule(
                    mood_id=mood["id"],
                    compatible_genres=compatible_genres or [1],
                    compatible_moods=compatible_moods or [1]
                )
            logger.info(f"Loaded {len(self.moods)} moods successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load moods from {file_path}: {str(e)}")
            return False

    def _build_compatibility_rules(self) -> bool:
        """Generate smart compatibility rules between genres/moods"""
        try:
            logger.debug("Building mood-to-genre mappings...")
            self._mood_to_genres = {
                mood_id: rule.compatible_genres
                for mood_id, rule in self.moods.items()
            }
            logger.debug(f"Mapped {len(self._mood_to_genres)} moods to genres.")

            self._build_similarity_matrix()
            logger.info("Compatibility rules and similarity matrix successfully built.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build compatibility rules: {str(e)}")
            return False

    def _build_similarity_matrix(self):
        """Build genre similarity matrix for hybrid recommendations"""
        num_genres = len(self.genres)
        self._genre_similarity_matrix = np.zeros((num_genres, num_genres))
        genre_ids = sorted(self.genres.keys())
        genre_index = {g_id: i for i, g_id in enumerate(genre_ids)}

        for g1_id, rule in self.genres.items():
            for g2_id in rule.compatible_genres:
                if g2_id in genre_index:
                    i = genre_index[g1_id]
                    j = genre_index[g2_id]
                    self._genre_similarity_matrix[i][j] = rule.weight
                    self._genre_similarity_matrix[j][i] = rule.weight
        logger.info(f"Built genre similarity matrix of shape {self._genre_similarity_matrix.shape}")

    def get_genre_compatibility(self, genre_id: int) -> List[int]:
        """Get compatible genres with fallback to defaults"""
        if genre_id not in self.genres:
            logger.warning(f"No compatibility rules found for genre {genre_id}")
            return self._get_default_compatible_genres()
        return self.genres[genre_id].compatible_genres

    def get_mood_compatibility(self, mood_id: int) -> List[int]:
        """Get compatible genres for mood with fallback to defaults"""
        return self._mood_to_genres.get(mood_id, self._get_default_compatible_genres())

    def get_genre_similarity(self, genre1_id: int, genre2_id: int) -> float:
        """Get similarity score between genres with fallback to 0"""
        if not self._genre_similarity_matrix:
            logger.warning("Genre similarity matrix is not initialized yet.")
            return 0.0
            
        genre_ids = sorted(self.genres.keys())
        try:
            i = genre_ids.index(genre1_id)
            j = genre_ids.index(genre2_id)
            return float(self._genre_similarity_matrix[i][j])
        except ValueError:
            logger.warning(f"Genre IDs {genre1_id} or {genre2_id} not found in index mapping.")
            return 0.0

    def get_compatible_items(self, genre_ids: Optional[List[int]], mood_ids: Optional[List[int]]) -> List[int]:
        """Get compatible items with empty input handling"""
        # Convert None to empty list
        genre_ids = genre_ids or []
        mood_ids = mood_ids or []
        
        # If both are empty, return default recommendations
        if not genre_ids and not mood_ids:
            return self._get_default_recommendations()
            
        # Normal compatibility logic here
        compatible_items = set()
        
        # Add items compatible with genres
        for genre_id in genre_ids:
            compatible_items.update(self.get_genre_compatibility(genre_id))
            
        # Add items compatible with moods
        for mood_id in mood_ids:
            compatible_items.update(self.get_mood_compatibility(mood_id))
            
        return list(compatible_items) or self._get_default_recommendations()

    def _get_default_recommendations(self) -> List[int]:
        """Fallback when no genres/moods are specified"""
        return self._default_recommendations

    def _get_default_compatible_genres(self) -> List[int]:
        """Default compatible genres when specific rules aren't found"""
        return [1, 2, 3]
    
    def get_compatible_movies(self, movie_genres: List[int], top_n: int = 10) -> List[int]:
        """Get compatible movie IDs based on genre rules with fallback protection
        
        Args:
            movie_genres: List of genre IDs to find compatible movies for
            top_n: Maximum number of recommendations to return
            
        Returns:
            List of compatible movie IDs (or default recommendations if no matches found)
        """
        try:
            if not movie_genres:
                logger.warning("No genres provided, returning default recommendations")
                return self._get_default_recommendations()[:top_n]
                
            # Get all compatible genres for the input genres
            compatible_genres = set()
            for genre_id in movie_genres:
                compatible_genres.update(self.get_genre_compatibility(genre_id))
            
            # Here you would normally query your database or lookup table
            # to find movies that match these compatible genres.
            # For now, we'll return dummy IDs as a placeholder.
            # In a real implementation, this would be replaced with:
            # return database_lookup(compatible_genres)[:top_n]
            
            logger.debug(f"Found {len(compatible_genres)} compatible genres for input {movie_genres}")
            dummy_movies = {
                1: [101, 102, 103, 104, 105],
                2: [201, 202, 203, 204],
                3: [301, 302, 303],
                # ... other genre mappings
            }
            
            # Get movies from all compatible genres
            compatible_movies = []
            for genre_id in compatible_genres:
                compatible_movies.extend(dummy_movies.get(genre_id, []))
                
            # Deduplicate and return top_n
            unique_movies = list(set(compatible_movies))
            return unique_movies[:top_n] or self._get_default_recommendations()[:top_n]
            
        except Exception as e:
            logger.error(f"Error in get_compatible_movies: {str(e)}")
            return self._get_default_recommendations()[:top_n]