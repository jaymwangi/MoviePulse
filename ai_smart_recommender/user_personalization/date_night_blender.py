import json
from typing import Dict, List, Tuple, Any
from uuid import uuid4
from pathlib import Path
import datetime

def weighted_avg_moods(mood_a: Dict[str, float], mood_b: Dict[str, float]) -> Dict[str, float]:
    """
    Enhanced mood blending with validation and normalization.
    """
    if not isinstance(mood_a, dict) or not isinstance(mood_b, dict):
        raise TypeError("Mood inputs must be dictionaries")
    
    all_moods = set(mood_a.keys()).union(set(mood_b.keys()))
    blended_moods = {}
    
    for mood in all_moods:
        score_a = max(0, min(1, mood_a.get(mood, 0)))  # Clamp to 0-1 range
        score_b = max(0, min(1, mood_b.get(mood, 0)))
        avg_score = round((score_a + score_b) / 2, 2)
        blended_moods[mood] = avg_score
    
    return blended_moods

def blend_genres(genres_a: List[str], genres_b: List[str]) -> List[str]:
    """
    Genre blending with case normalization and validation.
    """
    if not all(isinstance(g, str) for g in genres_a + genres_b):
        raise TypeError("All genres must be strings")
    
    # Normalize case and strip whitespace
    normalized_a = [g.strip().title() for g in genres_a]
    normalized_b = [g.strip().title() for g in genres_b]
    
    combined = list(set(normalized_a + normalized_b))
    return sorted(combined)


def blend_packs(pack_a: Dict[str, Any], pack_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modified to work with your movie-based packs without requiring genres.
    Focuses on blending moods while preserving movie data.
    """
    # Validate required fields
    REQUIRED_KEYS = {"moods"}  # Only require moods for blending
    
    for pack in [pack_a, pack_b]:
        missing = [k for k in REQUIRED_KEYS if k not in pack]
        if missing:
            raise ValueError(f"Pack missing required keys: {missing}")
        if not isinstance(pack["moods"], dict):
            raise ValueError("Pack moods must be a dictionary")

    # Blend moods
    blended_moods = {}
    all_moods = set(pack_a["moods"].keys()).union(set(pack_b["moods"].keys()))
    for mood in all_moods:
        score_a = pack_a["moods"].get(mood, 0)
        score_b = pack_b["moods"].get(mood, 0)
        blended_moods[mood] = round((score_a + score_b) / 2, 2)

    # Prepare result with all available data
    result = {
        "moods": blended_moods,
        "source_packs": [
            pack_a.get("name", "Pack A"),
            pack_b.get("name", "Pack B")
        ],
        "combined_at": datetime.datetime.now().isoformat(),
        "preference_weight": 0.7,
        # Preserve movie data if available
        "movies": {
            "pack_a": pack_a.get("movies", []),
            "pack_b": pack_b.get("movies", [])
        }
    }

    return result

def save_date_session(
    pack_a: Dict[str, Any],
    pack_b: Dict[str, Any],
    blended_prefs: Dict[str, Any],
    session_dir: str = "sessions"
) -> str:
    """
    Enhanced session saving with error recovery and backup.
    """
    session_id = str(uuid4())
    session_data = {
        "meta": {
            "session_id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "1.1"
        },
        "packs": {
            "a": {"name": pack_a.get("name"), "type": pack_a.get("type")},
            "b": {"name": pack_b.get("name"), "type": pack_b.get("type")}
        },
        "blended_prefs": blended_prefs,
        "system": {
            "saved_at": datetime.datetime.now().isoformat(),
            "success": False  # Will be set to True on successful save
        }
    }
    
    try:
        session_path = Path(session_dir)
        session_path.mkdir(exist_ok=True, parents=True)
        
        # Try JSON first
        main_file = session_path / "date_sessions.json"
        backup_file = session_path / f"backup_{session_id[:8]}.json"
        
        # Load existing or initialize new
        all_sessions = []
        if main_file.exists():
            with open(main_file, 'r') as f:
                all_sessions = json.load(f)
        
        # Append new session
        session_data["system"]["success"] = True
        all_sessions.append(session_data)
        
        # Save main file
        with open(main_file, 'w') as f:
            json.dump(all_sessions, f, indent=2)
            
        # Create backup copy
        with open(backup_file, 'w') as f:
            json.dump(session_data, f, indent=2)
            
    except Exception as e:
        # Fallback to simple text log
        error_log = session_path / "session_errors.log"
        with open(error_log, 'a') as f:
            f.write(f"{datetime.datetime.now()} - {session_id} - {str(e)}\n")
        raise RuntimeError(f"Session save failed: {e}") from e
    
    return session_id