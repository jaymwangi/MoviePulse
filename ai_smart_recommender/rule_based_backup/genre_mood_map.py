import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Set, Union
from collections import defaultdict
from functools import lru_cache
import warnings

class MoodGenreMapper:
    def __init__(
        self,
        mappings_path: Optional[Path] = None,
        compatibility_threshold: int = 2,
        conflict_sensitivity: float = 0.1
    ):
        """
        Initialize the mood-genre mapper with configurable settings.
        
        Args:
            mappings_path: Path to mood-genre mappings JSON file
            compatibility_threshold: Minimum genre overlaps for moods to be compatible
            conflict_sensitivity: How aggressively to flag conflicts (0.0-1.0)
        """
        self._mappings_path = (
            mappings_path 
            or Path(__file__).parent.parent.parent / "static_data" / "mood_genre_mappings.json"
        )
        self._compatibility_threshold = compatibility_threshold
        self._conflict_sensitivity = conflict_sensitivity
        self._mood_data = self._load_mood_mappings()
        self._compatibility_graph, self._conflict_scores = self._build_compatibility_graphs()
        self._genre_index = self._build_genre_index()

    def _load_mood_mappings(self) -> dict:
        """Load and validate mood-genre mappings from JSON file"""
        try:
            with open(self._mappings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate basic structure
            if not isinstance(data, dict):
                raise ValueError("Mappings file should contain a JSON object")
                
            for mood, config in data.items():
                if not isinstance(config.get("genres", []), list):
                    raise ValueError(f"Invalid genres format for mood: {mood}")
                if not isinstance(config.get("weight", 1.0), (int, float)):
                    raise ValueError(f"Invalid weight format for mood: {mood}")
                    
            return data
            
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Mood-genre mappings file not found at {self._mappings_path}"
            ) from e
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in {self._mappings_path}"
            ) from e

    def _build_compatibility_graphs(self) -> Tuple[Dict[str, Set[str]], Dict[Tuple[str, str], float]]:
        """
        Build compatibility graphs with conflict scoring.
        
        Returns:
            tuple: (compatibility_graph, conflict_scores)
        """
        graph = defaultdict(set)
        conflict_scores = defaultdict(float)
        all_moods = list(self._mood_data.keys())
        
        # Build from explicit pairs in data
        for mood, data in self._mood_data.items():
            for compatible in data.get("pairs_with", []):
                graph[mood].add(compatible)
                graph[compatible].add(mood)
        
        # Calculate implicit compatibility based on genre overlap
        for i, mood_a in enumerate(all_moods):
            for mood_b in all_moods[i+1:]:
                a_genres = set(self._mood_data[mood_a].get("genres", []))
                b_genres = set(self._mood_data[mood_b].get("genres", []))
                overlap = len(a_genres & b_genres)
                
                # If genres are too different, consider them incompatible
                if overlap < self._compatibility_threshold:
                    conflict_score = 1.0 - (overlap / self._compatibility_threshold)
                    conflict_scores[(mood_a, mood_b)] = conflict_score
                    conflict_scores[(mood_b, mood_a)] = conflict_score
                    
                    # Remove from compatibility graph if previously added
                    if mood_b in graph[mood_a]:
                        graph[mood_a].remove(mood_b)
                    if mood_a in graph[mood_b]:
                        graph[mood_b].remove(mood_a)
                elif mood_b not in graph[mood_a]:
                    # Add if not already explicitly defined
                    graph[mood_a].add(mood_b)
                    graph[mood_b].add(mood_a)
        
        return dict(graph), dict(conflict_scores)

    def _build_genre_index(self) -> Dict[int, Set[str]]:
        """Build reverse index from genre IDs to moods"""
        index = defaultdict(set)
        for mood, data in self._mood_data.items():
            for genre in data.get("genres", []):
                index[genre].add(mood)
        return dict(index)

    @lru_cache(maxsize=32)
    def mood_to_genres(
        self, 
        moods: Tuple[str], 
        strategy: str = 'weighted_union'
    ) -> Dict[str, Union[List[int], Dict[str, List[int]]]]:
        """
        Convert multiple moods to their genre mappings with different merge strategies.
        
        Args:
            moods: Tuple of mood strings (tuple for hashability with lru_cache)
            strategy: Merge strategy:
                - 'weighted_union': All genres with weights adjusted by compatibility (default)
                - 'union': All genres from all moods
                - 'intersection': Only genres common to all moods
                - 'individual': Keep genres separate per mood
        
        Returns:
            Dict with structure depending on strategy:
            - For 'union', 'intersection', 'weighted_union':
                {
                    "genres": list of genre IDs,
                    "weights": list of corresponding weights,
                    "strategy": strategy used
                }
            - For 'individual':
                {
                    "individual": {
                        mood: {
                            "genres": list of genre IDs,
                            "weight": float weight
                        }
                    },
                    "strategy": "individual"
                }
        """
        if not moods:
            return {"genres": [], "weights": [], "strategy": strategy}
            
        strategies = {
            'union': self._merge_union,
            'intersection': self._merge_intersection,
            'weighted_union': self._merge_weighted_union,
            'individual': self._merge_individual
        }
        
        if strategy not in strategies:
            raise ValueError(
                f"Unknown merge strategy: {strategy}. "
                f"Valid options: {list(strategies.keys())}"
            )
        
        result = strategies[strategy](moods)
        result["strategy"] = strategy
        return result

    def _merge_union(self, moods: Tuple[str]) -> Dict[str, List[int]]:
        """Merge all genres from all moods (no weight adjustment)"""
        genre_weights = defaultdict(float)
        for mood in moods:
            genres, weight = self.get_mood_genres(mood)
            for genre in genres:
                if genre not in genre_weights or weight > genre_weights[genre]:
                    genre_weights[genre] = weight
                    
        return {
            "genres": list(genre_weights.keys()),
            "weights": list(genre_weights.values())
        }

    def _merge_intersection(self, moods: Tuple[str]) -> Dict[str, List[int]]:
        """Only include genres present in all moods"""
        if not moods:
            return {"genres": [], "weights": []}
            
        common_genres = None
        total_weight = 0.0
        
        for mood in moods:
            genres, weight = self.get_mood_genres(mood)
            if common_genres is None:
                common_genres = set(genres)
            else:
                common_genres.intersection_update(genres)
            total_weight += weight
            
        avg_weight = total_weight / len(moods) if moods else 1.0
        return {
            "genres": list(common_genres) if common_genres else [],
            "weights": [avg_weight] * len(common_genres) if common_genres else []
        }

    def _merge_weighted_union(self, moods: Tuple[str]) -> Dict[str, List[int]]:
        """Merge with weights adjusted by mood compatibility"""
        genre_weights = defaultdict(float)
        mood_list = list(moods)
        
        # Calculate compatibility factors for each mood pair
        compat_factors = {}
        for i in range(len(mood_list)):
            for j in range(i+1, len(mood_list)):
                pair = tuple(sorted((mood_list[i], mood_list[j])))
                compat_factors[pair] = 1.0 - self._conflict_scores.get(pair, 0.0)
        
        for mood in mood_list:
            genres, base_weight = self.get_mood_genres(mood)
            
            # Calculate compatibility adjustment factor
            compat_adjustment = 1.0
            if len(mood_list) > 1:
                pair_compat = [
                    compat_factors[tuple(sorted((mood, other)))]
                    for other in mood_list if other != mood
                ]
                compat_adjustment = sum(pair_compat) / len(pair_compat)
            
            adj_weight = base_weight * compat_adjustment
            
            for genre in genres:
                if genre not in genre_weights or adj_weight > genre_weights[genre]:
                    genre_weights[genre] = adj_weight
        
        return {
            "genres": list(genre_weights.keys()),
            "weights": list(genre_weights.values())
        }

    def _merge_individual(self, moods: Tuple[str]) -> Dict[str, Dict[str, List[int]]]:
        """Keep genres separate for each mood"""
        individual = {}
        for mood in moods:
            genres, weight = self.get_mood_genres(mood)
            individual[mood] = {
                "genres": genres,
                "weight": weight
            }
        return {"individual": individual}

    def validate_mood_combos(
        self, 
        mood_combo: List[str], 
        strict: bool = False,
        return_all: bool = False
    ) -> Dict:
        """
        Validate combinations of moods for compatibility.
        
        Args:
            mood_combo: List of mood strings to validate
            strict: If True, all moods must be pairwise compatible
                   If False (default), majority must be compatible
            return_all: If True, return full compatibility matrix
        
        Returns:
            Dict with validation results:
            {
                "is_valid": bool,
                "incompatible_pairs": list of tuples,
                "suggestions": list of alternative moods,
                "compatibility_matrix": dict of dicts (if return_all=True),
                "confidence": float (0.0-1.0)
            }
        """
        if len(mood_combo) < 2:
            return {
                "is_valid": True,
                "incompatible_pairs": [],
                "suggestions": [],
                "confidence": 1.0
            }

        incompatible = []
        compatibility_matrix = defaultdict(dict)
        valid_pairs = set()

        # Build full compatibility matrix if requested
        for i in range(len(mood_combo)):
            for j in range(i+1, len(mood_combo)):
                mood_a = mood_combo[i]
                mood_b = mood_combo[j]
                pair = tuple(sorted((mood_a, mood_b)))
                
                if mood_b in self._compatibility_graph.get(mood_a, set()):
                    score = 1.0 - self._conflict_scores.get(pair, 0.0)
                    compatibility_matrix[mood_a][mood_b] = score
                    compatibility_matrix[mood_b][mood_a] = score
                    valid_pairs.add(pair)
                else:
                    score = self._conflict_scores.get(pair, 1.0)
                    compatibility_matrix[mood_a][mood_b] = score
                    compatibility_matrix[mood_b][mood_a] = score
                    incompatible.append((mood_a, mood_b, score))

        # Calculate overall confidence
        total_pairs = len(mood_combo) * (len(mood_combo) - 1) / 2
        if total_pairs > 0:
            valid_count = len(valid_pairs)
            conflict_scores = [s for _, _, s in incompatible]
            confidence = (
                valid_count + 
                sum(1 - s for s in conflict_scores)
            ) / total_pairs
        else:
            confidence = 1.0

        # Determine if combo is valid based on strictness
        if strict:
            is_valid = len(incompatible) == 0
        else:
            is_valid = confidence >= (1.0 - self._conflict_sensitivity)

        # Generate suggestions for incompatible pairs
        suggestions = []
        for a, b, score in incompatible:
            common_compatible = self._compatibility_graph.get(a, set()) & \
                               self._compatibility_graph.get(b, set())
            alternatives = [
                mood for mood in common_compatible
                if mood not in mood_combo
            ]
            
            # Sort alternatives by compatibility with original moods
            alternatives.sort(
                key=lambda x: (
                    self._compatibility_graph[a].get(x, 0) +
                    self._compatibility_graph[b].get(x, 0)
                ),
                reverse=True
            )
            
            suggestions.append({
                "pair": (a, b),
                "conflict_score": score,
                "alternatives": alternatives[:3]  # Top 3 suggestions
            })

        result = {
            "is_valid": is_valid,
            "incompatible_pairs": [(a, b) for a, b, _ in incompatible],
            "suggestions": suggestions,
            "confidence": confidence
        }
        
        if return_all:
            result["compatibility_matrix"] = dict(compatibility_matrix)
            
        return result

    def get_mood_genres(self, mood: str) -> Tuple[List[int], float]:
        """Get genre IDs and weight for a specific mood"""
        entry = self._mood_data.get(mood, {})
        return entry.get("genres", []), entry.get("weight", 1.0)

    def get_mood_metadata(self, mood: str) -> Optional[dict]:
        """Get complete metadata for a mood"""
        return self._mood_data.get(mood)

    def get_compatible_moods(self, mood: str) -> List[str]:
        """Get moods that pair well with the specified mood"""
        return list(self._compatibility_graph.get(mood, set()))

    def validate_movie_for_mood(
        self, 
        mood: str, 
        movie_data: dict
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Check if a movie meets validation metrics for a mood.
        
        Args:
            mood: Mood to validate against
            movie_data: Dictionary containing movie attributes:
                - vote_average: float (0-10)
                - runtime: int (minutes)
                - release_date: str (YYYY-MM-DD)
                - genres: list of genre IDs
        
        Returns:
            tuple: (is_valid, failure_reasons)
        """
        metrics = self._mood_data.get(mood, {}).get("validation_metrics", {})
        failures = {}
        
        # Rating check
        if 'min_rating' in metrics:
            if movie_data.get('vote_average', 0) < metrics['min_rating']:
                failures['rating'] = (
                    f"Rating {movie_data.get('vote_average', 'N/A')} "
                    f"< required {metrics['min_rating']}"
                )
        
        # Runtime check
        if 'max_runtime' in metrics:
            if movie_data.get('runtime', 0) > metrics['max_runtime']:
                failures['runtime'] = (
                    f"Runtime {movie_data.get('runtime', 'N/A')}min "
                    f"> max {metrics['max_runtime']}min"
                )
        
        # Decade check
        if 'decade_preference' in metrics:
            release_date = movie_data.get('release_date', '')
            if release_date:
                try:
                    release_year = int(release_date.split('-')[0])
                    preferred_decade = metrics['decade_preference']
                    if release_year // 10 != preferred_decade // 10:
                        failures['decade'] = (
                            f"Released in {release_year} "
                            f"(preferred {preferred_decade//10*10}s)"
                        )
                except (ValueError, IndexError):
                    failures['decade'] = "Invalid release date format"
        
        # Genre check
        if 'required_genres' in metrics:
            movie_genres = set(movie_data.get('genres', []))
            required = set(metrics['required_genres'])
            missing = required - movie_genres
            if missing:
                failures['genres'] = (
                    f"Missing required genres: {missing}"
                )
        
        return (not bool(failures)), failures

    def get_moods_for_genres(self, genres: List[int]) -> Set[str]:
        """Get all moods associated with any of the given genres"""
        result = set()
        for genre in genres:
            result.update(self._genre_index.get(genre, set()))
        return result

    def get_all_moods(self) -> List[str]:
        """Get list of all available moods"""
        return list(self._mood_data.keys())

    def to_dict(self) -> Dict:
        """Serialize current state for caching"""
        return {
            "mood_data": self._mood_data,
            "compatibility_graph": {
                k: list(v) for k, v in self._compatibility_graph.items()
            },
            "conflict_scores": self._conflict_scores,
            "genre_index": {
                k: list(v) for k, v in self._genre_index.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MoodGenreMapper':
        """Deserialize from cached state"""
        instance = cls.__new__(cls)
        instance._mood_data = data["mood_data"]
        instance._compatibility_graph = {
            k: set(v) for k, v in data["compatibility_graph"].items()
        }
        instance._conflict_scores = data["conflict_scores"]
        instance._genre_index = {
            k: set(v) for k, v in data["genre_index"].items()
        }
        instance._mappings_path = None  # Will be set if initialized normally
        instance._compatibility_threshold = 2
        instance._conflict_sensitivity = 0.1
        return instance


# Singleton instance for easy import
mood_mapper = MoodGenreMapper()

# Example usage
if __name__ == "__main__":
    try:
        # Initialize with custom settings
        mapper = MoodGenreMapper(
            compatibility_threshold=3,
            conflict_sensitivity=0.2
        )
        
        # Test mood_to_genres with different strategies
        print("\n=== mood_to_genres ===")
        test_moods = ("Uplifting", "Cozy", "Dark")
        
        print("Weighted Union:", mapper.mood_to_genres(test_moods))
        print("Union:", mapper.mood_to_genres(test_moods, "union"))
        print("Intersection:", mapper.mood_to_genres(test_moods, "intersection"))
        print("Individual:", mapper.mood_to_genres(test_moods, "individual"))
        
        # Test mood validation
        print("\n=== validate_mood_combos ===")
        print("Uplifting + Cozy:", mapper.validate_mood_combos(["Uplifting", "Cozy"]))
        print("Dark + Romantic:", mapper.validate_mood_combos(["Dark", "Romantic"]))
        print("Complex combo:", 
              mapper.validate_mood_combos(["Dark", "Uplifting", "Romantic"], return_all=True))
        
        # Test movie validation
        print("\n=== validate_movie_for_mood ===")
        test_movie = {
            "vote_average": 7.5,
            "runtime": 125,
            "release_date": "2015-06-15",
            "genres": [18, 10749]
        }
        print("For 'Romantic':", mapper.validate_movie_for_mood("Romantic", test_movie))
        print("For 'Exciting':", mapper.validate_movie_for_mood("Exciting", test_movie))
        
    except Exception as e:
        warnings.warn(f"Error in MoodGenreMapper: {str(e)}")