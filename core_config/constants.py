"""
Core Data Models for MoviePulse
-----------------------------
Defines fundamental data structures used across the application.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from enum import Enum  # <-- Add this import


@dataclass
class Genre:
    id: int
    name: str
    tmdb_id: Optional[int] = None  # Additional API reference

    def __post_init__(self):
        """Auto-set tmdb_id if not provided."""
        if self.tmdb_id is None:
            self.tmdb_id = self.id

@dataclass
class Person:
    id: int
    name: str
    role: str  # "actor", "director", etc.
    profile_path: Optional[str] = None
    known_for_department: Optional[str] = None  # Additional metadata

@dataclass
class Movie:
    id: int
    title: str
    overview: str
    release_date: str  # Format: "YYYY-MM-DD"
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None  # For detail pages
    vote_average: Optional[float] = None  # For sorting/filtering
    genres: List[Genre] = field(default_factory=list)
    cast: List[Person] = field(default_factory=list)
    directors: List[Person] = field(default_factory=list)
    runtime: Optional[int] = None
    similar_movies: Optional[List[int]] = field(default_factory=list)  # <-- ADD THIS

    @property
    def year(self) -> Optional[int]:
        try:
            return int(self.release_date[:4]) if self.release_date else None
        except (ValueError, TypeError):
            return None

@dataclass
class Video:
    key: str
    type: str
    site: str