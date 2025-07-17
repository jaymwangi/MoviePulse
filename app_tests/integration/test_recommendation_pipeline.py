import pytest
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
from service_clients.tmdb_client import TMDBClient
from ai_smart_recommender.recommender_engine.strategy_interfaces.content_based import ContentBasedStrategy
from ai_smart_recommender.recommender_engine.strategy_interfaces.contextual_rules import GenreRecommendationStrategy, MoodRecommendationStrategy
from ai_smart_recommender.recommender_engine.strategy_interfaces.actor_similarity import ActorSimilarityStrategy
from ai_smart_recommender.recommender_engine.orchestrator import Orchestrator

# --- Constants ---
TEST_MOVIE_ID = 123
USER_ID = "user123"
EMBEDDING_DIM = 384

# --- Expanded Mock Data ---
MOCK_MOVIE_DATA = {
    "123": {
        "id": 123,
        "title": "The Dark Knight",
        "genres": [{"id": 1, "name": "Action"}, {"id": 2, "name": "Thriller"}],
        "vote_average": 9.0,
        "poster_path": "/dark_knight.jpg",
        "cast": [{"id": 201, "name": "Christian Bale"}]
    },
    "456": {
        "id": 456,
        "title": "Inception",
        "genres": [{"id": 3, "name": "Sci-Fi"}, {"id": 1, "name": "Action"}],
        "vote_average": 8.8,
        "poster_path": "/inception.jpg",
        "cast": [{"id": 202, "name": "Leonardo DiCaprio"}]
    },
    "101": {
        "id": 101,
        "title": "Recent Movie",
        "genres": [{"id": 1, "name": "Action"}],
        "vote_average": 7.5,
        "poster_path": "/recent.jpg"
    },
    "102": {
        "id": 102,
        "title": "Older Movie",
        "genres": [{"id": 3, "name": "Sci-Fi"}],
        "vote_average": 7.0,
        "poster_path": "/older.jpg"
    }
}

MOCK_USER_PROFILE = {
    USER_ID: {
        "starter_pack": "cinephile",
        "genre_preferences": [1, 3],
        "mood": "thought-provoking",
        "last_watched": [
            {"id": 101, "timestamp": (datetime.now() - timedelta(days=1)).isoformat()},
            {"id": 102, "timestamp": (datetime.now() - timedelta(days=3)).isoformat()}
        ]
    }
}

MOCK_PACK_TO_GENRE = {
    "cinephile": [1, 3, 18],
    "casual_viewer": [35, 10749]
}

MOCK_ACTOR_SIMILARITY = {
    "201": {  # Christian Bale
        "similar_actors": [
            {"actor_id": 202, "score": 0.85, "common_movies": [123, 456]},  # Leonardo DiCaprio
            {"actor_id": 203, "score": 0.78, "common_movies": [123, 101]}
        ]
    }
}

@pytest.fixture
def rec_pipeline():
    with patch("ai_smart_recommender.recommender_engine.strategy_interfaces.actor_similarity.ActorSimilarityStrategy", autospec=True), \
         patch.object(TMDBClient, "get_person_filmography", return_value=[]), \
         patch.object(TMDBClient, "get_person_details", return_value=MagicMock(name="Dummy Actor")), \
         patch.object(TMDBClient, "get_movie_details") as mock_get_movie, \
         patch("ai_smart_recommender.recommender_engine.core_logic.embedding_engine.MovieEmbeddingEngine.generate_embeddings") as mock_load_embeddings, \
         patch("json.load") as mock_json_load, \
         patch("numpy.load") as mock_np_load:

        def get_movie_side_effect(movie_id):
            return MOCK_MOVIE_DATA.get(str(movie_id), MagicMock())

        mock_get_movie.side_effect = get_movie_side_effect

        # Create mock embeddings
        mock_embeddings = np.random.rand(len(MOCK_MOVIE_DATA), EMBEDDING_DIM)
        mock_load_embeddings.return_value = (
            mock_embeddings,
            list(map(int, MOCK_MOVIE_DATA.keys()))
        )

        mock_np_load.return_value = {
            'embeddings': mock_embeddings,
            'movie_ids': list(map(int, MOCK_MOVIE_DATA.keys()))
        }

        mock_json_load.side_effect = [MOCK_PACK_TO_GENRE, MOCK_MOVIE_DATA, MOCK_ACTOR_SIMILARITY]

        from ai_smart_recommender.interfaces.base_recommender import BaseRecommender
        from ai_smart_recommender.rec_pipeline import RecommendationPipeline

        # --- Fallback strategies ---
        fallback1 = MagicMock(spec=BaseRecommender,
                            should_activate=MagicMock(return_value=True),
                            strategy_type="fallback",
                            fallback_priority=1,
                            strategy_name="Fallback1")
        fallback1.execute.return_value = [
            MagicMock(
                content_id=301,
                score=0.7,
                strategy_used="fallback",
                title="Fallback Movie A",
                genres=[{"id": 1, "name": "Action"}]
            )
        ]

        fallback2 = MagicMock(spec=BaseRecommender,
                            should_activate=MagicMock(return_value=True),
                            strategy_type="fallback",
                            fallback_priority=2,
                            strategy_name="Fallback2")
        fallback2.execute.return_value = [
            MagicMock(
                content_id=302,
                score=0.65,
                strategy_used="fallback",
                title="Fallback Movie B",
                genres=[{"id": 2, "name": "Comedy"}]
            )
        ]

        pipeline = RecommendationPipeline(fallback_strategies=[fallback1, fallback2])

        # --- Primary strategy factory ---
        def create_strategy_instance(name, content_ids, can_fail=False):
            strategy = MagicMock(spec=BaseRecommender)
            strategy.should_activate = MagicMock(return_value=True)
            strategy.strategy_name = name
            strategy.strategy_type = "primary"
            if can_fail:
                strategy.execute.side_effect = Exception("Simulated failure")
            else:
                strategy.execute.return_value = [
                    MagicMock(
                        content_id=cid,
                        score=round(1.0 - i * 0.1, 2),
                        strategy_used=name,
                        title=f"{name} Movie {cid}",
                        genres=[{"id": i + 1, "name": f"Genre {i + 1}"}]
                    ) for i, cid in enumerate(content_ids)
                ]
            return strategy

        # --- Create and store primary strategies ---
        primary_strategies = [
            create_strategy_instance("content_based", [201, 202]),
            create_strategy_instance("genre_based", [203, 204]),
            create_strategy_instance("mood_based", [205, 206]),
            create_strategy_instance("actor_similarity", [207, 208]),
        ]

        # Add to pipeline and store references
        for strategy in primary_strategies:
            pipeline.add_primary_strategy(strategy)
        
        # Store strategies for test access
        pipeline._test_strategies = primary_strategies
        pipeline._test_fallbacks = [fallback1, fallback2]

        yield pipeline

        # Clean up
        for strategy in primary_strategies + [fallback1, fallback2]:
            strategy.reset_mock()


def test_cold_start_with_no_history(rec_pipeline):
    """Test pipeline handles cold start scenario"""
    recs = rec_pipeline.run({
        "user_profile": {
            "starter_pack": "casual_viewer",
            "genre_preferences": [],
            "last_watched": []
        },
        "limit": 3
    })
    assert len(recs) == 3
    # Verify fallbacks weren't used (since primary strategies should handle this)
    assert all("fallback" not in rec.strategy_used for rec in recs)


@pytest.mark.parametrize("limit", [1, 10, 50])
def test_limit_boundaries(rec_pipeline, limit):
    """Test pipeline respects limit boundaries"""
    recs = rec_pipeline.run({
        "target_movie_id": TEST_MOVIE_ID,
        "limit": limit
    })
    assert len(recs) <= limit
    # Verify no duplicate recommendations
    assert len(set(rec.content_id for rec in recs)) == len(recs)
    
def test_corrupted_embedding_cache(rec_pipeline):
    """Test pipeline handles corrupted embedding cache"""
    # Simulate cache corruption
    with patch("pickle.load", side_effect=Exception("Corrupted cache")):
        recs = rec_pipeline.run({
            "target_movie_id": TEST_MOVIE_ID,
            "limit": 3
        })
        

def test_all_strategies_represented(rec_pipeline):
    """Test all strategies contribute to recommendations"""
    recs = rec_pipeline.run({
        "target_movie_id": TEST_MOVIE_ID,
        "user_profile": MOCK_USER_PROFILE[USER_ID],
        "limit": 10
    })
    strategies_used = {rec.strategy_used for rec in recs}
    expected_strategies = {"content_based", "genre_based", "mood_based", "actor_similarity"}
    assert expected_strategies.issubset(strategies_used), \
        f"Missing strategies in recommendations. Expected: {expected_strategies}, Got: {strategies_used}"


def test_pipeline_happy_path(rec_pipeline):
    """Test pipeline returns recommendations with all expected strategies"""
    context = {
        "target_movie_id": TEST_MOVIE_ID,
        "user_profile": MOCK_USER_PROFILE[USER_ID],
        "limit": 5,
        "min_score": 0.5,
        "strategy": "hybrid",
        "enable_diversity": True
    }
    
    # Run the pipeline
    recs = rec_pipeline.run(context)
    
    # Verify we got recommendations
    assert len(recs) > 0, "No recommendations returned"
    
    # Verify at least one primary strategy was called
    primary_called = False
    for strategy in rec_pipeline._test_strategies:  # Use stored strategies
        if strategy.execute.called:
            primary_called = True
            break
    assert primary_called, "No primary strategies were executed"
    
    # Verify recommendation structure
    for rec in recs:
        assert hasattr(rec, 'content_id'), "Recommendation missing content_id"
        assert hasattr(rec, 'score'), "Recommendation missing score"
        assert hasattr(rec, 'strategy_used'), "Recommendation missing strategy_used"
        assert rec.score >= context["min_score"], f"Recommendation score below minimum: {rec.score}"
    
    # Verify we got recommendations from multiple strategies
    strategies_used = {rec.strategy_used for rec in recs}
    assert len(strategies_used) > 1, f"Only one strategy used: {strategies_used}"


def test_race_condition_handling(rec_pipeline):
    """Test pipeline properly handles race conditions"""
    # Get the actual mock strategies from the pipeline
    for strategy in rec_pipeline._test_strategies:  # Use stored strategies
        strategy.execute.side_effect = Exception("Simulated failure")

    context = {
        "target_movie_id": TEST_MOVIE_ID,
        "limit": 2
    }

    recs = rec_pipeline.run(context)
    assert len(recs) > 0, "Expected fallback recommendations but got none"
    assert all("fallback" in rec.strategy_used for rec in recs), \
        "Not all recommendations came from fallback strategies"


def test_freshness_priority(rec_pipeline):
    """Test pipeline prioritizes recent content"""
    # Modify the mock strategies to return the recent movie (101)
    for strategy in rec_pipeline._test_strategies:  # Use stored strategies
        strategy.execute.return_value = [
            MagicMock(
                content_id=101 if i == 0 else 102,  # First item is recent
                score=0.9 if i == 0 else 0.8,       # Higher score for recent
                strategy_used=strategy.strategy_name,
                title="Recent Movie" if i == 0 else "Older Movie",
                genres=[{"id": 1, "name": "Action"}]
            ) for i in range(2)
        ]
    
    context = {
        "user_profile": {
            "starter_pack": "cinephile",
            "last_watched": [
                {"id": 101, "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()},
                {"id": 102, "timestamp": (datetime.now() - timedelta(days=30)).isoformat()}
            ]
        },
        "limit": 5,
        "strategy": "hybrid",
        "enable_freshness": True
    }
    
    recs = rec_pipeline.run(context)
    
    # Verify recent movie is first in recommendations
    assert recs[0].content_id == 101, \
        f"Recent movie 101 should be first. Got: {[rec.content_id for rec in recs]}"
    
    # Additional check: verify the older movie is present but not first
    assert any(rec.content_id == 102 for rec in recs), \
        "Older movie should still be recommended"


def test_pipeline_returns_empty_when_all_strategies_fail(rec_pipeline):
    """Test pipeline returns empty list when all strategies fail"""
    # Force all strategies to fail
    for strategy in rec_pipeline._test_strategies:  # Primary strategies
        strategy.execute.side_effect = Exception("Simulated failure")
    for strategy in rec_pipeline._test_fallbacks:  # Fallback strategies
        strategy.execute.side_effect = Exception("Fallback failed")

    recs = rec_pipeline.run({
        "user_profile": {},
        "target_movie_id": "000000",
        "limit": 5
    })
    assert recs == [], "Expected empty list when all strategies fail"