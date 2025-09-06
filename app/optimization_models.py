"""
Core data models and enums for search optimization functionality.
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ConfigDict


class QueryComplexity(Enum):
    """Enum representing the complexity level of a search query."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class QueryIntent(Enum):
    """Enum representing the intent behind a search query."""
    FACTUAL = "factual"
    RESEARCH = "research"
    COMPARISON = "comparison"
    HOWTO = "howto"
    NEWS = "news"


class SummaryLength(Enum):
    """Enum representing the expected length of a summary."""
    SHORT = "short"      # 100-200 words
    MEDIUM = "medium"    # 300-600 words
    LONG = "long"        # 400-800 words


class DetailLevel(Enum):
    """Enum representing the level of detail in content generation."""
    CONCISE = "concise"
    BALANCED = "balanced"
    COMPREHENSIVE = "comprehensive"


@dataclass
class QueryAnalysis:
    """Data class containing the results of query analysis."""
    complexity: QueryComplexity
    domain: Optional[str]
    intent: QueryIntent
    expected_length: SummaryLength
    recency_importance: float  # 0.0-1.0 score for how important recent info is
    
    def __post_init__(self):
        """Validate recency_importance is within valid range."""
        if not 0.0 <= self.recency_importance <= 1.0:
            raise ValueError("recency_importance must be between 0.0 and 1.0")


@dataclass
class SourceScore:
    """Data class representing the scoring of a search result source."""
    url: str
    relevance_score: float      # 0.0-1.0
    authority_score: float      # 0.0-1.0
    freshness_score: float      # 0.0-1.0
    final_score: float          # weighted combination
    
    def __post_init__(self):
        """Validate all scores are within valid range."""
        scores = [self.relevance_score, self.authority_score, 
                 self.freshness_score, self.final_score]
        for score in scores:
            if not 0.0 <= score <= 1.0:
                raise ValueError("All scores must be between 0.0 and 1.0")


@dataclass
class ContentQuality:
    """Data class representing the quality assessment of scraped content."""
    relevance_score: float      # 0.0-1.0
    content_length: int
    information_density: float  # 0.0-1.0
    duplicate_content: bool
    quality_indicators: Dict[str, float]
    
    def __post_init__(self):
        """Validate scores and content length."""
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        if not 0.0 <= self.information_density <= 1.0:
            raise ValueError("information_density must be between 0.0 and 1.0")
        if self.content_length < 0:
            raise ValueError("content_length must be non-negative")


@dataclass
class SummaryConfig:
    """Data class for configuring summary generation."""
    target_length: int          # target word count
    detail_level: DetailLevel
    focus_areas: List[str]      # key topics to emphasize
    include_examples: bool
    
    def __post_init__(self):
        """Validate target_length is positive."""
        if self.target_length <= 0:
            raise ValueError("target_length must be positive")


@dataclass
class ScrapingResult:
    """Data class representing the result of a scraping operation."""
    url: str
    success: bool
    content: Optional[Dict] = None
    error: Optional[str] = None
    duration: float = 0.0
    
    def __post_init__(self):
        """Validate that successful results have content."""
        if self.success and self.content is None:
            raise ValueError("Successful scraping results must have content")
        if not self.success and self.error is None:
            raise ValueError("Failed scraping results must have an error message")


class EnhancedSource(BaseModel):
    """Enhanced source model extending the current source structure with optimization data."""
    url: HttpUrl
    title: str
    main_content: str
    images: List[Dict]
    categories: List[str]
    
    # New fields for optimization
    content_quality: Optional[ContentQuality] = None
    scraping_duration: Optional[float] = None
    relevance_score: Optional[float] = None
    word_count: Optional[int] = None
    last_updated: Optional[datetime] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
        
    def calculate_word_count(self) -> int:
        """Calculate and cache word count from main content."""
        if self.word_count is None:
            self.word_count = len(self.main_content.split())
        return self.word_count