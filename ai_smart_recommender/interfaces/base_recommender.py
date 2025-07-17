# ai_smart_recommender/interfaces/base_recommender.py
from abc import ABC, abstractmethod
from typing import Protocol, List, Dict, Any, runtime_checkable
from dataclasses import dataclass

@dataclass
class Recommendation:
    """
    Data structure for holding recommendation results with metadata.
    
    Attributes:
        movie_id: Unique identifier for the recommended movie
        title: Display title of the movie
        score: Confidence score (0.0-1.0) for the recommendation
        reason: Human-readable explanation for the recommendation
        metadata: Additional context about the recommendation
    """
    movie_id: int
    title: str
    score: float
    reason: str
    metadata: Dict[str, Any] = None

@runtime_checkable
class BaseRecommender(Protocol):
    """
    Protocol defining the interface that all recommendation strategies must implement.
    Ensures consistent behavior across different recommendation approaches.
    """
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """
        Unique identifier for the recommendation strategy.
        Used for logging and tracking recommendation sources.
        """
        pass
        
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> List[Recommendation]:
        """
        Execute the recommendation strategy based on provided context.
        
        Args:
            context: Dictionary containing all relevant input data for recommendations.
                    Common keys include:
                    - user_id: Optional user identifier
                    - genre_ids: List of preferred genre IDs
                    - actor_ids: List of preferred actor IDs
                    - limit: Maximum number of recommendations to return
                    - min_score: Minimum confidence threshold
        
        Returns:
            List of Recommendation objects. Must return empty list if no recommendations
            meet the criteria rather than returning low-quality matches.
        """
        pass

    def __str__(self) -> str:
        """Default string representation using the strategy name."""
        return f"{self.__class__.__name__}({self.strategy_name})"

@runtime_checkable
class FallbackStrategy(BaseRecommender, Protocol):
    """
    Extended interface for fallback recommendation strategies.
    Adds fallback-specific behavior while maintaining core recommender interface.
    """
    @property
    @abstractmethod
    def fallback_priority(self) -> int:
        """
        Priority level for fallback execution (lower numbers execute first).
        Used to determine fallback strategy sequence.
        """
        pass
        
    @abstractmethod
    def should_activate(self, context: Dict[str, Any]) -> bool:
        """
        Determine whether this fallback strategy should be activated.
        
        Args:
            context: Current recommendation context including any results
                    from primary strategies.
        
        Returns:
            Boolean indicating whether this fallback should execute.
        """
        pass