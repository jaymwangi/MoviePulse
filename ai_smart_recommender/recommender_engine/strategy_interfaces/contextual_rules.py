"""
Contextual Recommendation Strategies

Handles genre-based and mood-based recommendation strategies following the
RecommendationStrategy protocol. Updated with mood calendar integration.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Any, Optional
import json
from pathlib import Path
import logging
from datetime import datetime, date

from core_config import constants
from service_clients import tmdb_client
from ...rec_pipeline import Recommendation, BaseRecommender

logger = logging.getLogger(__name__)


@dataclass
class GenreRecommendationStrategy(BaseRecommender):
    """
    Genre-based recommendation strategy using genre similarity scoring.
    """
    genre_mappings: Dict[str, Dict]  # movie_id -> genre data
    strategy_name: str = "genre_based"

    @classmethod
    def from_json_file(cls, file_path: Path) -> 'GenreRecommendationStrategy':
        """Factory method to load from JSON data file"""
        try:
            with open(file_path, 'r') as f:
                mappings = json.load(f)
            logger.info(f"Loaded genre mappings for {len(mappings)} movies")
            return cls(genre_mappings=mappings)
        except Exception as e:
            logger.error(f"Failed to load genre mappings: {str(e)}")
            return cls(genre_mappings={})

    def execute(self, context: dict) -> List[Recommendation]:
        """
        Generate recommendations based on genre similarity.
        
        Args:
            context: Must contain 'genre_ids' (List[int]) and 'limit' (int)
            
        Returns:
            List of Recommendation objects sorted by genre match score
        """
        if not context.get('genre_ids'):
            return []

        target_genres = self._get_target_genres(context)
        scored_movies = self._score_movies_by_genre(target_genres)
        return self._format_recommendations(
            scored_movies[:context.get('limit', 5)],
            context
        )

    def _get_target_genres(self, context: dict) -> Set[str]:
        """Extract and validate target genres from context"""
        return set(str(g_id) for g_id in context['genre_ids'])

    def _score_movies_by_genre(self, target_genres: Set[str]) -> List[tuple]:
        """Score movies based on genre overlap"""
        scored = []
        for movie_id, data in self.genre_mappings.items():
            movie_genres = set(data.get('genre_ids', []))
            overlap = movie_genres & target_genres
            if overlap:
                score = len(overlap) / len(target_genres)
                scored.append((int(movie_id), score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _format_recommendations(
        self, 
        scored_movies: List[tuple], 
        context: dict
    ) -> List[Recommendation]:
        """Convert raw scores to Recommendation objects"""
        return [
            Recommendation(
                movie_id=movie_id,
                title=self._get_movie_title(movie_id),
                reason=f"Matched {score:.0%} of your preferred genres",
                score=score,
                strategy_used=self.strategy_name,
                metadata={
                    'genres': self._get_movie_genres(movie_id),
                    'match_score': score
                }
            )
            for movie_id, score in scored_movies
        ]

    def _get_movie_title(self, movie_id: int) -> str:
        """Get movie title with caching"""
        movie = tmdb_client.get_movie_details(movie_id)
        return getattr(movie, 'title', 'Unknown')

    def _get_movie_genres(self, movie_id: int) -> List[str]:
        """Get genre names for a movie"""
        movie = tmdb_client.get_movie_details(movie_id)
        return [g.name for g in getattr(movie, 'genres', [])]


class MoodRecommendationStrategy(BaseRecommender):
    """
    Mood-based recommendation strategy using mood-to-genre mappings.
    Now includes calendar integration for historical mood-based recommendations.
    """
    def __init__(
        self,
        mood_genre_map: Dict[str, Dict[str, Any]],
        genre_mappings: Dict[int, str],
        logger: logging.Logger = logger
    ):
        self.mood_genre_map = mood_genre_map or self._default_mood_map()
        self.genre_mappings = genre_mappings
        self.logger = logger
        self._mood_calendar_data = None

    @property
    def strategy_name(self) -> str:
        return "mood_based"

    @staticmethod
    def _default_mood_map() -> Dict[str, Dict[str, Any]]:
        """Fallback mood-to-genre map in case of missing data."""
        return {
            "uplifting": {
                "genres": [35, 10751, 10402],
                "weight": 1.2,
                "description": "Feel-good and inspiring"
            },
            "melancholic": {
                "genres": [18, 36, 10749],
                "weight": 1.0,
                "description": "Bittersweet and emotional"
            },
            "energetic": {
                "genres": [28, 12, 53],
                "weight": 1.1,
                "description": "High-energy and exciting"
            },
            "relaxing": {
                "genres": [14, 18, 9648],
                "weight": 0.9,
                "description": "Calm and soothing"
            },
            "romantic": {
                "genres": [10749, 35, 18],
                "weight": 1.1,
                "description": "Love and relationships focused"
            },
            "thoughtful": {
                "genres": [18, 9648, 878],
                "weight": 1.0,
                "description": "Intellectual and reflective"
            }
        }

    def _load_mood_calendar_data(self) -> Optional[Dict]:
        """Load mood calendar data from user profile if available"""
        if self._mood_calendar_data is None:
            try:
                from session_utils.user_profile import load_mood_calendar
                self._mood_calendar_data = load_mood_calendar()
                self.logger.info("Loaded mood calendar data for recommendations")
            except ImportError:
                self.logger.warning("Mood calendar module not available")
                self._mood_calendar_data = {}
            except Exception as e:
                self.logger.error(f"Failed to load mood calendar: {str(e)}")
                self._mood_calendar_data = {}
        return self._mood_calendar_data

    def get_mood_for_date(self, target_date: date) -> Optional[str]:
        """Get mood for a specific date from calendar data"""
        calendar_data = self._load_mood_calendar_data()
        if not calendar_data:
            return None
            
        date_str = target_date.isoformat()
        return calendar_data.get(date_str)

    def get_recent_moods(self, days: int = 7) -> Dict[str, int]:
        """Get frequency of moods over recent days"""
        calendar_data = self._load_mood_calendar_data()
        if not calendar_data:
            return {}
            
        recent_moods = {}
        today = datetime.now().date()
        
        for date_str, mood in calendar_data.items():
            try:
                entry_date = datetime.fromisoformat(date_str).date()
                if (today - entry_date).days <= days:
                    recent_moods[mood] = recent_moods.get(mood, 0) + 1
            except (ValueError, TypeError):
                continue
                
        return recent_moods

    def execute(self, context: dict) -> List[Recommendation]:
        """
        Generate recommendations based on a user's mood.
        Enhanced to support calendar-based mood history.
        
        Args:
            context: {
                'mood': str,                    # Direct mood input
                'date': date/datetime/str,      # Specific date for calendar lookup
                'recent_days': int,             # Analyze recent mood history
                'limit': int
            }

        Returns:
            List of Recommendation objects
        """
        # Determine which mood selection method to use
        target_moods = self._determine_target_moods(context)
        limit = context.get('limit', 5)
        
        if not target_moods:
            self.logger.warning("No target moods determined from context")
            return []

        # Get recommendations for all target moods
        all_recs = []
        for mood, weight in target_moods.items():
            mood_recs = self._get_mood_recommendations(mood, weight, limit * 2)
            all_recs.extend(mood_recs)

        # Deduplicate and sort by score
        unique_recs = self._deduplicate_recommendations(all_recs)
        return sorted(unique_recs, key=lambda x: x.score, reverse=True)[:limit]

    def _determine_target_moods(self, context: dict) -> Dict[str, float]:
        """Determine which moods to target based on context"""
        target_moods = {}
        
        # Direct mood input takes precedence
        if context.get('mood'):
            mood = context['mood'].lower()
            if mood in self.mood_genre_map:
                target_moods[mood] = self.mood_genre_map[mood].get("weight", 1.0)
            return target_moods
            
        # Date-specific mood from calendar
        if context.get('date'):
            date_obj = self._parse_date(context['date'])
            if date_obj:
                mood = self.get_mood_for_date(date_obj)
                if mood and mood in self.mood_genre_map:
                    target_moods[mood] = self.mood_genre_map[mood].get("weight", 1.0)
                    return target_moods

        # Recent mood analysis
        if context.get('recent_days'):
            recent_days = context['recent_days']
            recent_moods = self.get_recent_moods(recent_days)
            
            if recent_moods:
                total_entries = sum(recent_moods.values())
                for mood, count in recent_moods.items():
                    if mood in self.mood_genre_map:
                        frequency = count / total_entries
                        weight = self.mood_genre_map[mood].get("weight", 1.0)
                        target_moods[mood] = weight * frequency
                return target_moods

        return target_moods

    def _parse_date(self, date_input) -> Optional[date]:
        """Parse various date input formats"""
        if isinstance(date_input, date):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date()
        elif isinstance(date_input, str):
            try:
                return datetime.fromisoformat(date_input).date()
            except ValueError:
                try:
                    return datetime.strptime(date_input, "%Y-%m-%d").date()
                except ValueError:
                    return None
        return None

    def _get_mood_recommendations(self, mood: str, weight: float, limit: int) -> List[Recommendation]:
        """Get recommendations for a specific mood"""
        if mood not in self.mood_genre_map:
            return []

        mood_entry = self.mood_genre_map[mood]
        genre_ids = mood_entry["genres"]

        genre_context = {
            'genre_ids': genre_ids,
            'limit': limit,
            'mood': mood
        }

        genre_strategy = GenreRecommendationStrategy(self.genre_mappings)
        recs = genre_strategy.execute(genre_context)

        for rec in recs:
            rec.score *= weight
            rec.reason = f"Perfect for '{mood}' moods ({mood_entry['description']})"
            rec.metadata["mood"] = mood
            rec.metadata["mood_weight"] = weight
            rec.metadata["mood_description"] = mood_entry["description"]

        return recs

    def _deduplicate_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Remove duplicate recommendations, keeping the highest scored version"""
        unique_recs = {}
        for rec in recommendations:
            if rec.movie_id not in unique_recs or rec.score > unique_recs[rec.movie_id].score:
                unique_recs[rec.movie_id] = rec
        return list(unique_recs.values())


class MoodCalendarRecommendationStrategy(MoodRecommendationStrategy):
    """
    Specialized strategy for calendar-based mood recommendations.
    Provides additional methods for calendar integration.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.strategy_name = "mood_calendar_based"

    def get_mood_trend_analysis(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Analyze mood trends over a period for personalized recommendations.
        
        Returns:
            Dictionary with trend analysis and recommendation insights
        """
        recent_moods = self.get_recent_moods(period_days)
        total_entries = sum(recent_moods.values())
        
        if not total_entries:
            return {"message": "No mood data available for analysis"}
        
        # Calculate percentages
        mood_percentages = {
            mood: (count / total_entries) * 100
            for mood, count in recent_moods.items()
        }
        
        # Get dominant mood
        dominant_mood = max(recent_moods.items(), key=lambda x: x[1])[0] if recent_moods else None
        
        return {
            "period_days": period_days,
            "total_entries": total_entries,
            "mood_distribution": recent_moods,
            "mood_percentages": mood_percentages,
            "dominant_mood": dominant_mood,
            "recommendation_insights": self._generate_trend_insights(recent_moods, mood_percentages)
        }

    def _generate_trend_insights(self, mood_distribution: Dict[str, int], 
                               mood_percentages: Dict[str, float]) -> List[str]:
        """Generate insights based on mood trends"""
        insights = []
        
        if not mood_distribution:
            return ["Start tracking your moods to get personalized recommendations!"]
        
        # Check for mood diversity
        if len(mood_distribution) >= 4:
            insights.append("You have diverse mood patterns - we'll recommend a variety of content")
        elif len(mood_distribution) == 1:
            dominant_mood = list(mood_distribution.keys())[0]
            insights.append(f"Consistent {dominant_mood} mood pattern detected")
        
        # Check for specific mood patterns
        for mood, percentage in mood_percentages.items():
            if percentage > 50:
                insights.append(f"Strong preference for {mood} content ({percentage:.1f}% of time)")
            elif percentage > 30:
                insights.append(f"Frequent {mood} moods suggest you might enjoy related content")
        
        return insights

    def execute(self, context: dict) -> List[Recommendation]:
        """
        Generate recommendations with calendar context awareness.
        Enhanced to provide trend-based recommendations.
        """
        # Get trend analysis if requested
        if context.get('include_trend_analysis', False):
            trend_period = context.get('trend_period', 30)
            context['trend_analysis'] = self.get_mood_trend_analysis(trend_period)
        
        # Get standard mood recommendations
        recommendations = super().execute(context)
        
        # Add trend context to recommendations if available
        trend_analysis = context.get('trend_analysis')
        if trend_analysis and recommendations:
            dominant_mood = trend_analysis.get('dominant_mood')
            if dominant_mood:
                for rec in recommendations:
                    if rec.metadata.get('mood') == dominant_mood:
                        rec.reason += " (matches your frequent mood pattern)"
        
        return recommendations