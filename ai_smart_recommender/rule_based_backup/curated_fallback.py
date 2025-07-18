from dataclasses import dataclass
from pathlib import Path
import json
import random
from typing import List, Dict, Optional, Any
from ..interfaces.base_recommender import (
    Recommendation,
    FallbackStrategy  # Only need to inherit from FallbackStrategy
)

@dataclass
class CuratedSet:
    name: str
    movie_ids: List[int]
    genre: str

class CuratedFallback(FallbackStrategy):
    """
    Rule-based fallback system that surfaces handpicked movie sets when primary
    recommendation strategies return no results.
    Implements FallbackStrategy interface which includes BaseRecommender.
    """
    
    def __init__(self, data_dir: str = "static_data"):
        self.data_dir = Path(data_dir)
        self.curated_sets: List[CuratedSet] = []
        self._load_data()
        
    @property
    def strategy_name(self) -> str:
        return "curated_fallback"
        
    @property
    def fallback_priority(self) -> int:
        return 5  # Should be the last fallback to try
        
    def _load_data(self) -> None:
        """Load and validate the starter packs and genre mapping data."""
        try:
            # Load starter packs
            with open(self.data_dir / "starter_packs.json") as f:
                starter_packs: Dict[str, List[int]] = json.load(f)
            
            # Load genre mapping
            with open(self.data_dir / "pack_genres.json") as f:
                pack_genres: Dict[str, str] = json.load(f)
            
            # Validate and create curated sets
            for pack_name, movie_ids in starter_packs.items():
                if not isinstance(movie_ids, list) or not all(isinstance(id, int) for id in movie_ids):
                    raise ValueError(f"Invalid movie IDs format in pack: {pack_name}")
                
                genre = pack_genres.get(pack_name)
                if not genre:
                    raise ValueError(f"No genre mapping found for pack: {pack_name}")
                
                self.curated_sets.append(CuratedSet(
                    name=pack_name,
                    movie_ids=movie_ids,
                    genre=genre
                ))
                
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Data file not found: {e.filename}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
    
    def should_activate(self, context: Dict[str, Any]) -> bool:
        """Determine if this fallback should activate"""
        return context.get('fallback_required', False) and bool(self.curated_sets)
    
    def execute(self, context: Dict[str, Any]) -> List[Recommendation]:
            """
            Execute the fallback strategy to get recommendations.
            """
            if not self.curated_sets:
                return []

            preferred_genre = context.get('preferred_genre')
            num_recommendations = context.get('limit', 6)

            # Filter by genre if specified
            candidate_sets = [
                s for s in self.curated_sets
                if preferred_genre is None or s.genre.lower() == preferred_genre.lower()
            ] or self.curated_sets  # Fallback to all sets if no genre match

            selected_set = random.choice(candidate_sets)
            movie_ids = (
                selected_set.movie_ids 
                if len(selected_set.movie_ids) <= num_recommendations
                else random.sample(selected_set.movie_ids, num_recommendations)
            )

            return [
                Recommendation(
                    movie_id=movie_id,
                    title=f"Curated selection from {selected_set.name}",
                    score=0.85,
                    reason="Handpicked collection",
                    metadata={
                        "set_name": selected_set.name,
                        "genre": selected_set.genre
                    },
                    is_fallback=True  # Now this matches the class definition
                )
                for movie_id in movie_ids
            ]
    
    def get_all_curated_sets(self) -> List[Dict[str, str]]:
        """Get metadata about all available curated sets"""
        return [{
            "name": s.name,
            "genre": s.genre,
            "size": len(s.movie_ids)
        } for s in self.curated_sets]