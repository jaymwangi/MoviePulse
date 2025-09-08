# -*- coding: utf-8 -*-

import pytest
from ai_local_modules.tldr_summarizer import TLDRGenerator

# Test fixtures as inline dictionaries
@pytest.fixture
def generator():
    return TLDRGenerator()

# Movie data fixtures
@pytest.fixture
def matrix_movie():
    return {
        "title": "The Matrix",
        "overview": "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.",
        "genres": ["Action", "Sci-Fi"],
        "keywords": ["artificial reality", "cyberpunk", "fight", "future", "rebellion"]
    }

@pytest.fixture
def pulp_fiction_movie():
    return {
        "title": "Pulp Fiction",
        "overview": "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
        "genres": ["Crime", "Drama"],
        "keywords": ["nonlinear timeline", "violence", "drugs", "crime", "dark comedy"]
    }

@pytest.fixture
def short_overview_movie():
    return {
        "title": "Minimal Test Movie",
        "overview": "Short overview.",
        "genres": ["Comedy"],
        "keywords": ["funny"]
    }

@pytest.fixture
def no_overview_movie():
    return {
        "title": "No Overview Movie",
        "overview": "",
        "genres": ["Drama"],
        "keywords": ["emotional"]
    }

@pytest.fixture
def documentary_movie():
    return {
        "title": "A Documentary",
        "overview": "A factual examination of climate change impacts around the world.",
        "genres": ["Documentary"],
        "keywords": ["climate", "environment", "science"]
    }

@pytest.fixture
def mystery_movie():
    return {
        "title": "Murder Mystery",
        "overview": "A detective investigates a series of puzzling murders in a small town.",
        "genres": ["Mystery", "Thriller"],
        "keywords": ["investigation", "crime scene", "whodunit"]
    }

@pytest.fixture
def romance_movie():
    return {
        "title": "The Notebook",
        "overview": "A poor yet passionate young man falls in love with a rich young woman, giving her a sense of freedom, but they are soon separated because of their social differences.",
        "genres": ["Romance", "Drama"],
        "keywords": ["love story", "1940s", "summer romance", "memory", "notebook"]
    }

# Parameterized test cases for content flags
content_flag_test_cases = [
    # (movie_data, expected_flags)
    (
        {
            "title": "Violent Movie",
            "overview": "A brutal fight scene with blood and gore everywhere. People get killed in horrific ways.",
            "genres": ["Action"],
            "keywords": ["violence", "blood", "murder"]
        },
        ["🔪 Violence"]
    ),
    (
        {
            "title": "Explicit Movie",
            "overview": "Contains explicit sexual content and nudity throughout the film.",
            "genres": ["Drama"],
            "keywords": ["sensual", "intimate scenes"]
        },
        ["🔥 Sexuality"]
    ),
    (
        {
            "title": "Drug Movie",
            "overview": "Story about drug abuse and addiction with scenes of substance use.",
            "genres": ["Drama"],
            "keywords": ["drug abuse", "addiction"]
        },
        ["💊 Drugs"]
    ),
    (
        {
            "title": "Language Movie",
            "overview": "Characters use foul language and cursing throughout the film.",
            "genres": ["Comedy"],
            "keywords": ["profanity", "swearing"]
        },
        ["💢 Language"]
    ),
    (
        {
            "title": "Clean Movie",
            "overview": "A family-friendly adventure suitable for all ages.",
            "genres": ["Family", "Adventure"],
            "keywords": ["wholesome", "fun"]
        },
        []
    )
]

class TestTLDRGenerator:
    """Test suite for TLDRGenerator class"""
    
    def test_generate_tldr_returns_expected_structure(self, generator, matrix_movie):
        """Test that generate_tldr returns a dictionary with expected keys"""
        result = generator.generate_tldr(matrix_movie)
        
        assert isinstance(result, dict)
        assert "summary" in result
        assert "themes" in result
        assert "content_flags" in result
        assert "is_fallback" in result
        
        assert isinstance(result["summary"], str)
        assert isinstance(result["themes"], list)
        assert isinstance(result["content_flags"], list)
        assert isinstance(result["is_fallback"], bool)
    
    def test_summary_length_limit(self, generator, matrix_movie):
        """Test that summary does not exceed 120 characters"""
        result = generator.generate_tldr(matrix_movie)
        
        assert len(result["summary"]) <= 120, f"Summary exceeds 120 chars: {len(result['summary'])}"
    
    def test_themes_count(self, generator, matrix_movie):
        """Test that themes list contains 2-3 items"""
        result = generator.generate_tldr(matrix_movie)
        
        assert 2 <= len(result["themes"]) <= 3, f"Expected 2-3 themes, got {len(result['themes'])}"
    
    def test_fallback_for_short_overview(self, generator, short_overview_movie):
        """Test that fallback is used for short overviews"""
        result = generator.generate_tldr(short_overview_movie)
        
        assert result["is_fallback"] is True
        assert len(result["summary"]) <= 120
    
    def test_fallback_for_no_overview(self, generator, no_overview_movie):
        """Test that fallback is used when no overview is provided"""
        result = generator.generate_tldr(no_overview_movie)
        
        assert result["is_fallback"] is True
        assert len(result["summary"]) > 0
    
    def test_empty_movie_data(self, generator):
        """Test handling of empty movie data"""
        result = generator.generate_tldr({})
        
        assert result["is_fallback"] is True
        assert len(result["summary"]) > 0
    
    def test_none_movie_data(self, generator):
        """Test handling of None movie data"""
        result = generator.generate_tldr(None)
        
        assert result["is_fallback"] is True
        assert len(result["summary"]) > 0
    
    @pytest.mark.parametrize("movie_data,expected_flags", content_flag_test_cases)
    def test_content_flags_detection(self, generator, movie_data, expected_flags):
        """Test content flag detection with various inputs"""
        result = generator.generate_tldr(movie_data)
        
        assert set(result["content_flags"]) == set(expected_flags), \
            f"Expected flags: {expected_flags}, Got: {result['content_flags']}"
    
    def test_documentary_themes(self, generator, documentary_movie):
        """Test theme extraction for documentary movies"""
        result = generator.generate_tldr(documentary_movie)
        
        assert len(result["themes"]) >= 1
        # Documentary should map to factual/real events themes
        assert any(theme.lower() in ["documentary", "factual", "real events"] 
                  for theme in result["themes"])
    
    def test_mystery_themes(self, generator, mystery_movie):
        """Test theme extraction for mystery movies"""
        result = generator.generate_tldr(mystery_movie)
        
        assert len(result["themes"]) >= 1
        # Mystery should map to investigation/enigmatic themes
        assert any(theme.lower() in ["mystery", "investigation", "enigmatic", "whodunit"] 
                  for theme in result["themes"])
    
    def test_romance_themes(self, generator, romance_movie):
        """Test theme extraction for romance movies"""
        result = generator.generate_tldr(romance_movie)
        
        assert len(result["themes"]) >= 1
        # Romance should map to love story/romantic themes
        assert any(theme.lower() in ["romance", "love story", "romantic"] 
                  for theme in result["themes"])
    
    def test_violent_content_flags(self, generator, pulp_fiction_movie):
        """Test content flag detection for movies with violent content"""
        result = generator.generate_tldr(pulp_fiction_movie)
        
        # Pulp Fiction should have violence and possibly drugs flags
        assert any("violence" in flag.lower() for flag in result["content_flags"])
    
    def test_summary_not_empty(self, generator, matrix_movie):
        """Test that summary is never empty"""
        result = generator.generate_tldr(matrix_movie)
        
        assert len(result["summary"]) > 0
        assert result["summary"].strip() != ""
    
    def test_themes_not_empty(self, generator, matrix_movie):
        """Test that themes list is never empty"""
        result = generator.generate_tldr(matrix_movie)
        
        assert len(result["themes"]) > 0
        assert all(theme.strip() != "" for theme in result["themes"])
    
    def test_fallback_summary_creation(self, generator):
        """Test fallback summary creation with minimal data"""
        minimal_movie = {
            "title": "Test Movie",
            "overview": "Short",
            "genres": ["Drama"],
            "keywords": ["test"]
        }
        
        result = generator.generate_tldr(minimal_movie)
        
        assert result["is_fallback"] is True
        assert len(result["summary"]) > 0
        assert len(result["themes"]) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])