import json
from pathlib import Path
from core_config import constants

# Mood-Genre Mappings
MOOD_GENRE_MAPPINGS = {
    "Uplifting": {
        "genres": [35, 10751, 10402],  # Comedy, Family, Music
        "weight": 1.2,
        "description": "Feel-good, motivating, inspiring films to boost your mood"
    },
    "Melancholic": {
        "genres": [18, 36, 10749],  # Drama, History, Romance
        "weight": 1.0,
        "description": "Bittersweet, reflective, sometimes tragic stories that evoke deep emotion"
    },
    "Exciting": {
        "genres": [28, 12, 53],  # Action, Adventure, Thriller
        "weight": 1.3,
        "description": "Fast-paced, action-packed, adrenaline-fueled experiences"
    },
    "Romantic": {
        "genres": [10749, 18, 35],  # Romance, Drama, Comedy
        "weight": 1.1,
        "description": "Heartwarming love stories, romance and relationships"
    },
    "Chill": {
        "genres": [10751, 35, 10402],  # Family, Comedy, Music
        "weight": 0.9,
        "description": "Easygoing, relaxed, cozy vibes, perfect for downtime"
    },
    "Suspenseful": {
        "genres": [53, 9648, 80],  # Thriller, Mystery, Crime
        "weight": 1.2,
        "description": "Nail-biting tension, twists, thrillers, and mystery"
    },
    "Dark": {
        "genres": [80, 27, 18],  # Crime, Horror, Drama
        "weight": 1.0,
        "description": "Gritty, serious, sometimes disturbing themes"
    },
    "Empowering": {
        "genres": [18, 28, 10752],  # Drama, Action, War
        "weight": 1.2,
        "description": "Strong characters overcoming odds, leaving you inspired"
    },
    "Whimsical": {
        "genres": [14, 16, 10751],  # Fantasy, Animation, Family
        "weight": 1.1,
        "description": "Playful, imaginative, lighthearted, and fantastical"
    },
    "Thought-Provoking": {
        "genres": [18, 878, 9648],  # Drama, Science Fiction, Mystery
        "weight": 1.0,
        "description": "Movies that challenge your mind or world view"
    }
}

# Template User Preferences
USER_PREFERENCES_TEMPLATE = {
    "preferred_genres": [],
    "preferred_moods": [],
    "watch_history": [],
    "disliked_genres": [],
    "disliked_moods": [],
    "preferred_actors": [],
    "preferred_directors": []
}

def generate_files():
    # Create mood-genre mappings
    with open(constants.MOOD_GENRE_MAPPINGS, "w") as f:
        json.dump(MOOD_GENRE_MAPPINGS, f, indent=2)
    
    # Create empty user preferences template
    with open(constants.USER_PREFERENCES_FILE, "w") as f:
        json.dump(USER_PREFERENCES_TEMPLATE, f, indent=2)

if __name__ == "__main__":
    constants.RECOMMENDER_DATA_DIR.mkdir(exist_ok=True)
    generate_files()
