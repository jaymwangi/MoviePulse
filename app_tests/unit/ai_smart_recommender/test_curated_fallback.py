"""
Unit Tests for Curated Fallback Recommendation System

Updated to strictly comply with BaseRecommender and FallbackStrategy protocols
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from typing import Dict, List

from ai_smart_recommender.rule_based_backup.curated_fallback import (
    CuratedFallback,
    CuratedSet
)
from ai_smart_recommender.interfaces.base_recommender import (
    Recommendation,
    BaseRecommender,
    FallbackStrategy
)

# Sample test data
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data" / "curated_fallback"

@pytest.fixture
def sample_starter_packs() -> Dict[str, List[int]]:
    return {
        "Staff Picks": [1, 2, 3, 4, 5],
        "Rainy Day": [6, 7, 8],
        "Action Pack": [9, 10]
    }

@pytest.fixture
def sample_pack_genres() -> Dict[str, str]:
    return {
        "Staff Picks": "Drama",
        "Rainy Day": "Comedy",
        "Action Pack": "Action"
    }

@pytest.fixture
def mock_data_files(sample_starter_packs, sample_pack_genres, tmp_path):
    """Create temporary test data files"""
    packs_file = tmp_path / "starter_packs.json"
    genres_file = tmp_path / "pack_genres.json"
    
    with open(packs_file, 'w') as f:
        json.dump(sample_starter_packs, f)
    
    with open(genres_file, 'w') as f:
        json.dump(sample_pack_genres, f)
    
    return tmp_path

@pytest.fixture
def loaded_fallback(mock_data_files):
    """Fixture providing a fully loaded CuratedFallback instance"""
    return CuratedFallback(data_dir=mock_data_files)

class TestInterfaceCompliance:
    """Tests to verify protocol compliance"""
    
    def test_implements_base_recommender(self, mock_data_files):
        """Should implement BaseRecommender protocol"""
        fallback = CuratedFallback(data_dir=mock_data_files)
        assert isinstance(fallback, BaseRecommender)
    
    def test_implements_fallback_strategy(self, mock_data_files):
        """Should implement FallbackStrategy protocol"""
        fallback = CuratedFallback(data_dir=mock_data_files)
        assert isinstance(fallback, FallbackStrategy)
    
    def test_has_required_properties(self, mock_data_files):
        """Should have required protocol properties"""
        fallback = CuratedFallback(data_dir=mock_data_files)
        assert hasattr(fallback, 'strategy_name')
        assert hasattr(fallback, 'fallback_priority')
        assert fallback.strategy_name == "curated_fallback"
        assert isinstance(fallback.fallback_priority, int)
    
    def test_has_required_methods(self, mock_data_files):
        """Should have required protocol methods"""
        fallback = CuratedFallback(data_dir=mock_data_files)
        assert hasattr(fallback, 'execute')
        assert hasattr(fallback, 'should_activate')

class TestRecommendationOutput:
    """Tests for recommendation output format compliance"""
    
    @pytest.fixture
    def loaded_fallback(self, mock_data_files):
        return CuratedFallback(data_dir=mock_data_files)
    
    def test_execute_returns_proper_type(self, loaded_fallback):
        """Should return List[Recommendation]"""
        result = loaded_fallback.execute({"limit": 3})
        assert isinstance(result, list)
        assert all(isinstance(rec, Recommendation) for rec in result)
    
    def test_recommendation_fields_populated(self, loaded_fallback):
        """Should populate all required Recommendation fields"""
        with patch("random.choice", side_effect=lambda x: x[0]):  # Pick first set
            recs = loaded_fallback.execute({"limit": 1})
            
            assert recs[0].movie_id in [1, 2, 3, 4, 5]
            assert "Staff Picks" in recs[0].title
            assert 0 <= recs[0].score <= 1
            assert isinstance(recs[0].reason, str)
            assert isinstance(recs[0].metadata, dict)
            assert "set_name" in recs[0].metadata
    
    def test_sets_fallback_flag(self, loaded_fallback):
        """Should mark recommendations as fallbacks"""
        recs = loaded_fallback.execute({"limit": 1})
        assert all(rec.is_fallback for rec in recs)

class TestFallbackBehavior:
    """Tests for fallback-specific behavior"""
    
    @pytest.fixture
    def loaded_fallback(self, mock_data_files):
        return CuratedFallback(data_dir=mock_data_files)
    
    def test_should_activate_conditions(self, loaded_fallback):
        """should_activate should follow expected logic"""
        # Should activate when fallback_required is True
        assert loaded_fallback.should_activate({"fallback_required": True})
        
        # Should not activate when fallback_required is False
        assert not loaded_fallback.should_activate({"fallback_required": False})
        
        # Should not activate when no curated sets available
        with patch.object(loaded_fallback, 'curated_sets', []):
            assert not loaded_fallback.should_activate({"fallback_required": True})
    
    def test_fallback_priority(self, loaded_fallback):
        """Should have appropriate priority for fallback sequence"""
        # Curated should be last in fallback sequence
        assert loaded_fallback.fallback_priority > 4  # Higher than other fallbacks

   
class TestIntegrationScenarios:
    """End-to-end integration scenarios"""
    
    def test_full_fallback_flow(self, mock_data_files):
        """Test complete fallback scenario"""
        fallback = CuratedFallback(data_dir=mock_data_files)
        
        # Simulate primary strategies failing
        context = {
            "fallback_required": True,
            "limit": 2,
            "preferred_genre": "Action"
        }
        
        recs = fallback.execute(context)
        
        # Verify results
        assert len(recs) == 2
        assert all(rec.movie_id in [9, 10] for rec in recs)
        assert all(rec.metadata["set_name"] == "Action Pack" for rec in recs)
        assert all(rec.is_fallback for rec in recs)


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_empty_data_handling(self, tmp_path):
        """Should handle empty data files gracefully"""
        with open(tmp_path / "starter_packs.json", 'w') as f:
            json.dump({}, f)
        with open(tmp_path / "pack_genres.json", 'w') as f:
            json.dump({}, f)
        
        fallback = CuratedFallback(data_dir=tmp_path)
        assert fallback.execute({"limit": 3}) == []
        assert not fallback.should_activate({"fallback_required": True})
    
    def test_missing_context_fields(self, loaded_fallback):
        """Should handle missing context fields gracefully"""
        # No limit specified
        recs = loaded_fallback.execute({})
        assert len(recs) > 0  # Should use default limit
        
        # No fallback_required flag
        assert not loaded_fallback.should_activate({})