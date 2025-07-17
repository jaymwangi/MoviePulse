# ai_smart_recommender/rec_pipeline.py
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from operator import attrgetter
from .interfaces.base_recommender import BaseRecommender, Recommendation
from .interfaces.fallback_rules import FallbackStrategy, create_fallback_system
from .config import constants, settings

logger = logging.getLogger(__name__)

class RecommendationPipeline:
    """
    Main recommendation pipeline that orchestrates multiple recommendation strategies
    with primary and fallback execution flows, now supporting strategy weighting.
    """
    def __init__(self, fallback_strategies: Optional[List[FallbackStrategy]] = None):
        """Initialize pipeline with optional fallback strategies"""
        self.primary_strategies: List[Tuple[BaseRecommender, float]] = []
        self.fallback_strategies: List[Tuple[FallbackStrategy, float]] = []
        self._initialized = False

        # ✅ Use injected fallback strategies if provided
        try:
            if fallback_strategies is not None:
                self.fallback_strategies = sorted(
                    [(s, s.fallback_priority) for s in fallback_strategies],
                    key=lambda x: x[1]  # Sort by priority
                )
            else:
                self.fallback_strategies = sorted(
                    [(s, s.fallback_priority) for s in create_fallback_system()],
                    key=lambda x: x[1]
                )
            logger.info(f"Loaded {len(self.fallback_strategies)} fallback strategies")
        except Exception as e:
            logger.error("Failed to initialize fallback strategies", exc_info=settings.DEBUG)

    def initialize(self) -> None:
        """Optional explicit initialization hook"""
        self._initialized = True
        logger.info("Recommendation pipeline initialized")

    @property
    def is_ready(self) -> bool:
        """Check if pipeline has strategies configured"""
        return bool(self.primary_strategies or self.fallback_strategies)

    def add_primary_strategy(self, strategy: BaseRecommender, weight: float = 1.0) -> None:
        """Add a weighted strategy to the primary recommendation flow"""
        if not isinstance(strategy, BaseRecommender):
            raise ValueError("Primary strategy must implement BaseRecommender")
        if weight <= 0:
            raise ValueError("Strategy weight must be positive")
            
        self.primary_strategies.append((strategy, weight))
        logger.debug(
            f"Added primary strategy: {strategy.strategy_name} "
            f"(weight: {weight}, total: {len(self.primary_strategies)})"
        )

    def add_fallback_strategy(self, strategy: FallbackStrategy, weight: float = 0.5) -> None:
        """Add a weighted strategy to the fallback sequence with priority sorting"""
        if not isinstance(strategy, FallbackStrategy):
            raise ValueError("Fallback strategy must implement FallbackStrategy")
        if weight <= 0:
            raise ValueError("Strategy weight must be positive")
            
        self.fallback_strategies.append((strategy, weight))
        self.fallback_strategies.sort(key=lambda x: x[0].fallback_priority)
        logger.debug(
            f"Added fallback strategy: {strategy.strategy_name} "
            f"(priority: {strategy.fallback_priority}, weight: {weight}, "
            f"total: {len(self.fallback_strategies)})"
        )

    def run(self, context: Dict) -> List[Recommendation]:
        """
        Execute the recommendation pipeline with the given context.
        Applies strategy weights to recommendation scores.
        
        Args:
            context: Dictionary containing all recommendation parameters
            
        Returns:
            List of Recommendation objects sorted by weighted score
        """
        if not self.is_ready:
            logger.warning("Pipeline has no strategies configured")
            return []
            
        context = self._prepare_context(context)
        recommendations = self._execute_primary_strategies(context)
        
        if self._needs_fallback(recommendations, context):
            recommendations = self._execute_fallback_strategies(recommendations, context)
            
        return self._post_process(recommendations, context)

    def _prepare_context(self, context: Dict) -> Dict:
        """Prepare and validate the context dictionary"""
        context.setdefault('limit', constants.DEFAULT_REC_LIMIT)
        context.setdefault('enable_diversity', True)
        return context

    def _execute_primary_strategies(self, context: Dict) -> List[Recommendation]:
        """Execute all primary strategies with weight application"""
        recommendations = []
        
        for strategy, weight in self.primary_strategies:
            try:
                if results := strategy.execute(context):
                    for rec in results:
                        rec.score *= weight  # Apply weight to score
                        rec.source_strategy = strategy.strategy_name
                        rec.is_fallback = False
                    recommendations.extend(results)
                    logger.debug(
                        f"Primary strategy {strategy.strategy_name} "
                        f"(weight: {weight}) returned {len(results)} recommendations"
                    )
                    
                    if len(recommendations) >= context['limit']:
                        break
                        
            except Exception as e:
                logger.error(
                    f"Primary strategy {strategy.strategy_name} failed: {str(e)}",
                    exc_info=settings.DEBUG
                )
                
        return recommendations

    def _needs_fallback(self, 
                       recommendations: List[Recommendation], 
                       context: Dict) -> bool:
        """Determine if fallback strategies should be activated"""
        return (
            not recommendations or 
            len(recommendations) < context['limit'] or
            context.get('force_fallback', False)
        )

    def _execute_fallback_strategies(self, 
                                   recommendations: List[Recommendation],
                                   context: Dict) -> List[Recommendation]:
        """Execute fallback strategies with weight application"""
        for fallback, weight in self.fallback_strategies:
            if not fallback.should_activate(context):
                continue
                
            try:
                if results := fallback.execute(context):
                    for rec in results:
                        rec.score *= weight  # Apply weight to score
                        rec.source_strategy = fallback.strategy_name
                        rec.is_fallback = True
                    recommendations.extend(results)
                    logger.info(
                        f"Activated fallback: {fallback.strategy_name} "
                        f"(priority: {fallback.fallback_priority}, weight: {weight})"
                    )
                    break
                    
            except Exception as e:
                logger.error(
                    f"Fallback {fallback.strategy_name} failed: {str(e)}",
                    exc_info=settings.DEBUG
                )
                
        return recommendations

    def _post_process(self, 
                     recommendations: List[Recommendation], 
                     context: Dict) -> List[Recommendation]:
        """Apply all post-processing steps to recommendations"""
        if not recommendations:
            return []
            
        # Sort by weighted score (descending)
        recommendations.sort(key=attrgetter('score'), reverse=True)
        
        # Apply diversity if enabled
        if context['enable_diversity']:
            recommendations = self._apply_diversity(recommendations, context)
            
        return recommendations[:context['limit']]

    def _apply_diversity(self, 
                       recs: List[Recommendation], 
                       context: Dict) -> List[Recommendation]:
        """Apply diversity controls to recommendations"""
        try:
            from recommender_engine.diversity_control import cluster_analyzer
            diversity_factor = context.get(
                'diversity_factor', 
                constants.DEFAULT_DIVERSITY_FACTOR
            )
            return cluster_analyzer.diversify(recs, diversity_factor)
            
        except ImportError:
            logger.warning("Diversity module not available - skipping")
            return recs
            
        except Exception as e:
            logger.error(f"Diversity application failed: {str(e)}")
            return recs