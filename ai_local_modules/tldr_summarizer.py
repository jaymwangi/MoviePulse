# -*- coding: utf-8 -*-

# ai_engine/summarizer/tldr_generator.py

import re
from typing import Dict, List, Set, Optional
from collections import Counter

class TLDRGenerator:
    """
    Generate TL;DR summaries for movies with:
    - GPT-style one-liner (≤120 chars)
    - 2-3 key themes extraction
    - Content-safety flags
    - Fallback logic
    """
    
    # Theme mapping based on genres and keywords
    THEME_MAPPING = {
        # Action themes
        'action': ['thrilling', 'action-packed', 'high-octane', 'explosive'],
        'adventure': ['epic journey', 'quest', 'adventure-filled'],
        'superhero': ['superhero spectacle', 'heroic tale', 'comic book adventure'],
        
        # Drama themes
        'drama': ['emotional', 'heartfelt', 'compelling drama', 'character-driven'],
        'romance': ['romantic', 'love story', 'heartwarming'],
        'comedy': ['hilarious', 'comedy', 'funny', 'humorous'],
        
        # Genre themes
        'sci-fi': ['sci-fi spectacle', 'futuristic', 'technological'],
        'fantasy': ['fantastical', 'magical', 'mythical'],
        'horror': ['terrifying', 'horror', 'chilling', 'scary'],
        'thriller': ['suspenseful', 'thriller', 'edge-of-your-seat'],
        'crime': ['criminal underworld', 'crime saga', 'gangster'],
        'documentary': ['factual', 'real events', 'biographical', 'documentary'],
        'mystery': ['enigmatic', 'puzzle', 'whodunit', 'mysterious', 'investigation'],
        
        # Mood/thematic elements
        'inspiring': ['inspiring', 'uplifting', 'motivational'],
        'thought-provoking': ['thought-provoking', 'philosophical', 'deep'],
        'dark': ['dark', 'gritty', 'bleak'],
        'lighthearted': ['lighthearted', 'fun', 'entertaining'],
        'family': ['family-friendly', 'heartwarming', 'wholesome']
    }
    
    # Genre to theme normalization mapping
    GENRE_TO_THEME = {
        'science fiction': 'sci-fi',
        'sci fi': 'sci-fi',
        'scifi': 'sci-fi',
        'science-fiction': 'sci-fi',
        'sci-fy': 'sci-fi',  # Common misspelling
        'fantasy': 'fantasy',
        'horror': 'horror',
        'thriller': 'thriller',
        'action': 'action',
        'adventure': 'adventure',
        'comedy': 'comedy',
        'drama': 'drama',
        'romance': 'romance',
        'animation': 'family',
        'family': 'family',
        'documentary': 'documentary',
        'crime': 'crime',
        'mystery': 'mystery'
    }
    
    # Content flag indicators with weights
    CONTENT_FLAGS = {
        'violence': {
            'gore': 2, 'brutal': 2, 'torture': 2,  # High weight indicators
            'violence': 1, 'blood': 1, 'fight': 1, 'shoot': 1, 'kill': 1, 'murder': 1, 'war': 1
        },
        'language': {
            'foul language': 1, 'cursing': 1, 'profanity': 1, 'swearing': 1, 'curse words': 1
        },
        'sexuality': {
            'explicit': 2, 'graphic': 2,  # High weight indicators
            'sexual content': 1, 'nudity': 1, 'sensual': 1, 'intimate': 1, 'sex': 1
        },
        'drugs': {
            'drug abuse': 2, 'addiction': 2,  # High weight indicators
            'drug use': 1, 'alcohol': 1, 'smoking': 1, 'substance': 1
        }
    }
    
    EMOJI_MAP = {
        'violence': '🔪',
        'language': '💢',
        'sexuality': '🔥',
        'drugs': '💊'
    }
    
    def __init__(self):
        self.fallback_threshold = 50  # Min chars for overview to be considered valid
        self.summary_length_limit = 120
        self.max_themes = 3
    
    def generate_tldr(self, movie_data: Dict) -> Dict:
        """
        Generate a complete TL;DR summary for a movie.
        
        Args:
            movie_data: Dictionary containing movie metadata with keys:
                - overview (str): Movie description/synopsis
                - genres (list): List of genre names
                - keywords (list, optional): List of keyword/tag strings
                - title (str, optional): Movie title
                
        Returns:
            Dictionary with:
                - summary: GPT-style one-liner (≤120 chars)
                - themes: List of 2-3 key themes
                - content_flags: List of content warning flags with emojis
                - is_fallback: Boolean indicating if fallback was used
        """
        # Validate input
        if not movie_data or 'overview' not in movie_data:
            return self._create_fallback_response("No movie data provided")
            
        overview = movie_data.get('overview', '')
        genres = movie_data.get('genres', [])
        keywords = movie_data.get('keywords', [])
        title = movie_data.get('title', 'Unknown Movie')
        
        # Check if we need to use fallback
        if len(overview) < self.fallback_threshold:
            return self._create_fallback_response(overview, title, genres, keywords)
        
        try:
            # Generate the components
            summary = self._generate_summary(overview, genres, keywords)
            themes = self._extract_themes(overview, genres, keywords)
            content_flags = self._identify_content_flags(overview, keywords)
            
            return {
                'summary': summary,
                'themes': themes,
                'content_flags': content_flags,
                'is_fallback': False
            }
            
        except Exception as e:
            # If anything fails, use fallback
            return self._create_fallback_response(overview, title, genres, keywords)
    
    def _generate_summary(self, overview: str, genres: List[str], keywords: List[str]) -> str:
        """
        Enhanced summary generation with sentence scoring.
        """
        # Split into sentences more robustly
        sentences = re.split(r'(?<=[.!?])\s+', overview)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not valid_sentences:
            return self._create_basic_summary(genres, keywords)
        
        # Score sentences based on relevance
        genre_words = [g.lower() for g in genres]
        keyword_words = [k.lower() for k in keywords]
        scored_sentences = []
        
        for sentence in valid_sentences:
            sentence_lower = sentence.lower()
            # Calculate relevance score
            relevance_score = sum(3 for word in genre_words if word in sentence_lower)
            relevance_score += sum(2 for word in keyword_words if word in sentence_lower)
            
            # Bonus for being the first sentence
            if sentence == valid_sentences[0]:
                relevance_score += 1
                
            scored_sentences.append((sentence, relevance_score, len(sentence)))
        
        # Sort by score (highest first), then by length (shorter first for conciseness)
        scored_sentences.sort(key=lambda x: (-x[1], x[2]))
        
        # Select the best sentence that fits the length limit
        best_sentence = scored_sentences[0][0]
        for sentence, score, length in scored_sentences:
            if length <= self.summary_length_limit:
                best_sentence = sentence
                break
        
        # Ensure character limit
        if len(best_sentence) > self.summary_length_limit:
            # Smart truncation at sentence boundary or word boundary
            if '.' in best_sentence[:self.summary_length_limit - 3]:
                trunc_point = best_sentence.rfind('.', 0, self.summary_length_limit - 3)
                best_sentence = best_sentence[:trunc_point + 1]
            else:
                # Truncate at word boundary
                words = best_sentence.split()
                truncated = []
                char_count = 0
                
                for word in words:
                    if char_count + len(word) + 1 <= self.summary_length_limit - 3:
                        truncated.append(word)
                        char_count += len(word) + 1
                    else:
                        break
                
                best_sentence = ' '.join(truncated) + '...'
        
        return best_sentence[:self.summary_length_limit]
    
    def _create_basic_summary(self, genres: List[str], keywords: List[str]) -> str:
        """Create a basic summary when overview is poor."""
        if genres and keywords:
            return f"A {genres[0].lower()} about {keywords[0]}"
        elif genres:
            return f"An engaging {genres[0].lower()} story"
        elif keywords:
            return f"A story about {keywords[0]}"
        return "An engaging cinematic experience"
    
    def _normalize_genre(self, genre: str) -> str:
        """Normalize genre names to match theme mapping."""
        genre_lower = genre.lower().strip()
        
        # Replace spaces and dashes with hyphens for consistency
        normalized = re.sub(r'[\s\-]+', '-', genre_lower)
        
        # Check if we have a direct mapping
        if normalized in self.GENRE_TO_THEME:
            return self.GENRE_TO_THEME[normalized]
        
        # Return the normalized version as fallback
        return normalized
    
    def _extract_themes(self, overview: str, genres: List[str], keywords: List[str]) -> List[str]:
        """
        Improved theme extraction with better scoring - using canonical theme names.
        """
        theme_scores = Counter()
        text_corpus = overview.lower() + ' ' + ' '.join(keywords).lower()
        
        # Score themes based on multiple factors
        for theme, indicators in self.THEME_MAPPING.items():
            score = 0
            
            # Genre relevance with normalization
            for genre in genres:
                normalized_genre = self._normalize_genre(genre)
                if normalized_genre == theme:
                    score += 3
            
            # Indicator matches in overview and keywords using word boundaries
            for indicator in indicators:
                # Use regex with word boundaries for precision
                pattern = r'\b' + re.escape(indicator) + r'\b'
                if re.search(pattern, text_corpus):
                    score += 2
                if any(re.search(pattern, k.lower()) for k in keywords):
                    score += 1
            
            if score > 0:
                # Store score against the canonical theme name
                theme_scores[theme] = score
        
        # Get top themes and capitalize for UI consistency
        top_themes = [t.capitalize() for t, _ in theme_scores.most_common(self.max_themes)]
        
        # Ensure we have at least 2 themes with deduplication
        if len(top_themes) < 2 and genres:
            # Use genre-based themes as fallback
            genre_based = []
            for genre in genres[:2]:
                normalized = self._normalize_genre(genre)
                if normalized in self.THEME_MAPPING:
                    theme_name = normalized.capitalize()
                    if theme_name not in top_themes:  # Avoid duplicates
                        genre_based.append(theme_name)
                else:
                    theme_name = f"{genre} story".capitalize()
                    if theme_name not in top_themes:  # Avoid duplicates
                        genre_based.append(theme_name)
            
            top_themes.extend(genre_based[:2 - len(top_themes)])
        
        # Final deduplication while preserving order
        return list(dict.fromkeys(top_themes))[:self.max_themes]
    
    def _identify_content_flags(self, overview: str, keywords: List[str]) -> List[str]:
        """
        Weighted content flag detection using regex with word boundaries.
        """
        content_flags = set()
        text_to_analyze = overview.lower() + ' ' + ' '.join(k.lower() for k in keywords)
        
        for flag_type, indicators in self.CONTENT_FLAGS.items():
            total_score = 0
            
            # Score based on weighted indicators
            for indicator, weight in indicators.items():
                # Use regex with word boundaries for precision
                pattern = r'\b' + re.escape(indicator) + r'\b'
                matches = len(re.findall(pattern, text_to_analyze))
                total_score += matches * weight
            
            # Threshold for flagging (adjust as needed)
            if total_score >= 2:
                content_flags.add(f"{self.EMOJI_MAP.get(flag_type, '⚠️')} {flag_type.capitalize()}")
        
        return sorted(content_flags)
    
    def _create_fallback_response(self, overview: str, title: str = "Unknown Movie", 
                                 genres: List[str] = [], keywords: List[str] = []) -> Dict:
        """
        Create a fallback response when the overview is too short or generation fails.
        """
        # Create a simple summary from what we have
        if overview and len(overview) > 10:
            fallback_summary = overview[:100] + ('...' if len(overview) > 100 else '')
        else:
            # Use genres and keywords to create a better fallback summary
            fallback_summary = self._create_basic_summary(genres, keywords)
        
        # Ensure summary is within character limit
        fallback_summary = fallback_summary[:self.summary_length_limit]
        
        # Create more interesting fallback themes
        themes = []
        if genres:
            # Use genre-specific fallback themes
            for genre in genres[:self.max_themes]:
                normalized = self._normalize_genre(genre)
                if normalized in self.THEME_MAPPING:
                    theme_name = normalized.capitalize()
                    if theme_name not in themes:  # Avoid duplicates
                        themes.append(theme_name)
                else:
                    theme_name = f"{genre} drama".capitalize()
                    if theme_name not in themes:  # Avoid duplicates
                        themes.append(theme_name)
        else:
            themes = ["Compelling story"]
        
        # Add keyword-based themes if we have space
        if len(themes) < self.max_themes and keywords:
            for keyword in keywords[:self.max_themes - len(themes)]:
                theme_name = keyword.capitalize()
                if theme_name not in themes:  # Avoid duplicates
                    themes.append(theme_name)
        
        return {
            'summary': fallback_summary,
            'themes': themes[:self.max_themes],
            'content_flags': [],
            'is_fallback': True
        }


# Test with multiple movies to see the improved output
if __name__ == "__main__":
    generator = TLDRGenerator()
    
    # Test movies
    test_movies = [
        {
            "title": "The Matrix",
            "overview": "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.",
            "genres": ["Action", "Sci-Fi"],
            "keywords": ["artificial reality", "cyberpunk", "fight", "future", "rebellion"]
        },
        {
            "title": "Finding Nemo",
            "overview": "After his son is captured in the Great Barrier Reef and taken to Sydney, a timid clownfish sets out on a journey to bring him home.",
            "genres": ["Animation", "Adventure", "Comedy", "Family"],
            "keywords": ["fish", "ocean", "father son relationship", "quest", "underwater"]
        },
        {
            "title": "Pulp Fiction",
            "overview": "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
            "genres": ["Crime", "Drama"],
            "keywords": ["nonlinear timeline", "violence", "drugs", "crime", "dark comedy"]
        },
        {
            "title": "The Notebook",
            "overview": "A poor yet passionate young man falls in love with a rich young woman, giving her a sense of freedom, but they are soon separated because of their social differences.",
            "genres": ["Romance", "Drama"],
            "keywords": ["love story", "1940s", "summer romance", "memory", "notebook"]
        },
        {
            "title": "Minimal Test Movie",
            "overview": "Short overview.",
            "genres": ["Comedy"],
            "keywords": ["funny"]
        },
        {
            "title": "A Documentary",
            "overview": "A factual examination of climate change impacts around the world.",
            "genres": ["Documentary"],
            "keywords": ["climate", "environment", "science"]
        },
        {
            "title": "Murder Mystery",
            "overview": "A detective investigates a series of puzzling murders in a small town.",
            "genres": ["Mystery", "Thriller"],
            "keywords": ["investigation", "crime scene", "whodunit"]
        }
    ]
    
    for i, movie in enumerate(test_movies, 1):
        print(f"=== Movie {i}: {movie['title']} ===")
        result = generator.generate_tldr(movie)
        print(f"Summary: {result['summary']} ({len(result['summary'])} chars)")
        print(f"Themes: {', '.join(result['themes'])}")
        print(f"Content Flags: {', '.join(result['content_flags']) or 'None'}")
        print(f"Fallback: {result['is_fallback']}")
        print()