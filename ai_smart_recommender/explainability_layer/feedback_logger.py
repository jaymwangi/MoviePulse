"""
Enhanced Feedback Logger with Fallback Strategy Tracking

Features:
1. Tracks all recommendation strategies with special handling for curated fallback
2. Rotating log files to prevent unbounded growth
3. Type hints for better code clarity
4. Prevention of duplicate logging
5. Comprehensive analytics integration
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
from logging.handlers import RotatingFileHandler

from core_config import constants
from ..interfaces.base_recommender import Recommendation

# Type aliases for better readability
Context = Dict[str, Any]
LogData = Dict[str, Any]

class FallbackStrategyType(Enum):
    """Enumeration of fallback strategy types"""
    GENRE = "genre_fallback"
    MOOD = "mood_fallback"
    ACTOR = "actor_fallback"
    POPULARITY = "popularity_fallback"
    CURATED = "curated_fallback"

class FeedbackLogger:
    """Centralized logging for recommendation feedback and analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger("recommendation.analytics")
        self.logger.propagate = False  # Prevent duplicate logging
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Configure logging with rotation and JSON formatting"""

        # Ensure the logs directory exists
        Path(constants.ANALYTICS_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            constants.ANALYTICS_LOG_PATH,
            maxBytes=5_000_000,  # 5MB per file
            backupCount=5        # Keep 5 rotated files
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)


    def log_recommendation_batch(
        self,
        recommendations: List[Recommendation],
        context: Context,
        execution_time: float
    ) -> None:
        """
        Log a complete recommendation batch with strategy breakdown
        
        Args:
            recommendations: List of Recommendation objects
            context: Original request context
            execution_time: Total processing time in seconds
        """
        strategy_counts = self._count_strategies(recommendations)
        fallback_strategy = self._detect_fallback_strategy(recommendations)
        
        log_data: LogData = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": context.get("request_id", "unknown"),
            "user_id": context.get("user_id"),
            "strategy_distribution": strategy_counts,
            "execution_time": execution_time,
            "recommendation_count": len(recommendations),
            "context_summary": self._sanitize_context(context),
            "fallback_used": fallback_strategy is not None,
            "fallback_strategy": fallback_strategy.value if fallback_strategy else None
        }
        
        self._log_json_data(log_data)
        
        # Special logging for curated fallback
        if fallback_strategy == FallbackStrategyType.CURATED:
            self._log_curated_fallback(recommendations, context)

    def _log_curated_fallback(
        self,
        recommendations: List[Recommendation],
        context: Context
    ) -> None:
        """Specialized logging for curated fallback events"""
        curated_recs = [
            rec for rec in recommendations 
            if rec.source_strategy == FallbackStrategyType.CURATED.value
        ]
        
        if not curated_recs:
            return
            
        set_names = {rec.metadata.get("set_name", "unknown") for rec in curated_recs}
        
        log_data: LogData = {
            "event_type": "curated_fallback_used",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": context.get("request_id", "unknown"),
            "user_id": context.get("user_id"),
            "curated_sets": list(set_names),
            "recommendation_count": len(curated_recs),
            "context": self._sanitize_context(context),
            "special_note": "Curated recommendations served"
        }
        
        self._log_json_data(log_data)

    def log_fallback_activation(
        self,
        strategy_type: FallbackStrategyType,
        context: Context,
        reason: str
    ) -> None:
        """
        Log when a fallback strategy is activated
        
        Args:
            strategy_type: Type of fallback strategy
            context: Request context
            reason: Why the fallback was activated
        """
        log_data: LogData = {
            "event_type": "fallback_activation",
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": strategy_type.value,
            "reason": reason,
            "context": self._sanitize_context(context)
        }
        
        self._log_json_data(log_data)
        
        # Special case for curated fallback
        if strategy_type == FallbackStrategyType.CURATED:
            self._log_json_data({
                **log_data,
                "special_note": "Curated fallback activated as last resort"
            })

    def _log_json_data(self, data: LogData) -> None:
        """Helper method for consistent JSON logging"""
        self.logger.info(json.dumps(data, default=str))

    def _count_strategies(self, recommendations: List[Recommendation]) -> Dict[str, int]:
        """Count occurrences of each strategy in recommendations"""
        counts: Dict[str, int] = {}
        for rec in recommendations:
            counts[rec.source_strategy] = counts.get(rec.source_strategy, 0) + 1
        return counts

    def _detect_fallback_strategy(
        self,
        recommendations: List[Recommendation]
    ) -> Optional[FallbackStrategyType]:
        """Identify which fallback strategy was used (if any)"""
        for rec in recommendations:
            if rec.is_fallback:
                try:
                    return FallbackStrategyType(rec.source_strategy)
                except ValueError:
                    continue
        return None

    def _sanitize_context(self, context: Context) -> Context:
        """Remove sensitive or overly verbose context fields"""
        return {
            k: v for k, v in context.items()
            if k not in [
                'user_prefs', 
                'explicit_filters',
                'sensitive_data',
                'auth_token'
            ] and not k.startswith('_')
        }

# Singleton instance for easy access
feedback_logger = FeedbackLogger()
