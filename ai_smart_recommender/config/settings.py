from .constants import *
import logging

# Logging Config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Fallback Strategy Order
FALLBACK_PRIORITIES = {
    'genre_mood': 1,
    'actor_based': 2,
    'popularity': 3
}
DEBUG = True