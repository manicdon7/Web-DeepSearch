"""
Unit tests for optimization data models and enums.
"""
import pytest
from datetime import datetime
from app.optimization_models import (
    QueryComplexity, QueryIntent, SummaryLength, DetailLevel,
    QueryAnalysis, SourceScore, ContentQuality, SummaryConfig, EnhancedSource
)


class TestEnums:
    """Test cases for all enum classes."""
    
    def test_query_complexity_enum(self):
        """Test QueryComplexity enum values."""
        assert QueryComplexity.SIMPLE.value == "simple"
        assert QueryComplexity.MODERATE.value == "moderate"
        assert QueryComplexity.COMPLEX.value == "complex"
        
        # Test enum membership
        assert QueryComplexity.SIMPLE in QueryComplexity
        assert len(QueryComplexity) == 3
    
    def test_query_intent_enum(self):
        """Test QueryIntent enum values."""
        assert QueryIntent.FACTUAL.value == "factual"
        assert QueryIntent.RESEARCH.value == "research"
        assert QueryIntent.COMPARISON.value == "comparison"
        assert QueryIntent.HOWTO.value == "howto"
        assert QueryIntent.NEWS.value == "news"
        
        # Test enum membership
        assert QueryIntent.FACTUAL in QueryIntent
        assert len(QueryIntent) == 5
    
    def test_summary_length_enum(self):
        """Test SummaryLength enum values."""
        assert SummaryLength.SHORT.value == "short"
        assert SummaryLength.MEDIUM.value == "medium"
        assert SummaryLength.LONG.value == "long"
        
        # Test enum membership
        assert SummaryLength.SHORT in SummaryLength
        assert len(SummaryLength) == 3
    
    def test_detail_level_enum(self):
        """Test DetailLevel enum values."""
        assert DetailLevel.CONCISE.value == "concise"
        assert DetailLevel.BALANCED.value == "balanced"
        assert DetailLevel.COMPREHENSIVE.value == "comprehensive"
        
        # Test enum membership
        assert DetailLevel.CONCISE in DetailLevel
        assert len(DetailLevel) == 3


class TestQueryAnalysis:
    """Test cases for QueryAnalysis dataclass."""
    
    def test_valid_query_analysis_creation(self):
        """Test creating a valid QueryAnalysis instance."""
        analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain="technology",
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.7
        )
        
        assert analysis.complexity == QueryComplexity.MODERATE
        assert analysis.domain == "technology"
        assert analysis.intent == QueryIntent.RESEARCH
        assert analysis.expected_length == SummaryLength.MEDIUM
        assert analysis.recency_importance == 0.7
    
    def test_query_analysis_with_none_domain(self):
        """Test QueryAnalysis with None domain."""
        analysis = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain=None,
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.3
        )
        
        assert analysis.domain is None
        assert analysis.complexity == QueryComplexity.SIMPLE
    
    def test_query_analysis_recency_importance_validation(self):
        """Test validation of recency_importance field."""
        # Valid boundary values
        QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain=None,
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.0
        )
        
        QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain=None,
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=1.0
        )
        
        # Invalid values should raise ValueError
        with pytest.raises(ValueError, match="recency_importance must be between 0.0 and 1.0"):
            QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain=None,
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=-0.1
            )
        
        with pytest.raises(ValueError, match="recency_importance must be between 0.0 and 1.0"):
            QueryAnalysis(
                complexity=QueryComplexity.SIMPLE,
                domain=None,
                intent=QueryIntent.FACTUAL,
                expected_length=SummaryLength.SHORT,
                recency_importance=1.1
            )


class TestSourceScore:
    """Test cases for SourceScore dataclass."""
    
    def test_valid_source_score_creation(self):
        """Test creating a valid SourceScore instance."""
        score = SourceScore(
            url="https://example.com",
            relevance_score=0.8,
            authority_score=0.9,
            freshness_score=0.6,
            final_score=0.75
        )
        
        assert score.url == "https://example.com"
        assert score.relevance_score == 0.8
        assert score.authority_score == 0.9
        assert score.freshness_score == 0.6
        assert score.final_score == 0.75
    
    def test_source_score_boundary_values(self):
        """Test SourceScore with boundary values."""
        # Valid boundary values
        SourceScore(
            url="https://test.com",
            relevance_score=0.0,
            authority_score=0.0,
            freshness_score=0.0,
            final_score=0.0
        )
        
        SourceScore(
            url="https://test.com",
            relevance_score=1.0,
            authority_score=1.0,
            freshness_score=1.0,
            final_score=1.0
        )
    
    def test_source_score_validation(self):
        """Test validation of score fields."""
        # Test invalid relevance_score
        with pytest.raises(ValueError, match="All scores must be between 0.0 and 1.0"):
            SourceScore(
                url="https://test.com",
                relevance_score=-0.1,
                authority_score=0.5,
                freshness_score=0.5,
                final_score=0.5
            )
        
        # Test invalid authority_score
        with pytest.raises(ValueError, match="All scores must be between 0.0 and 1.0"):
            SourceScore(
                url="https://test.com",
                relevance_score=0.5,
                authority_score=1.1,
                freshness_score=0.5,
                final_score=0.5
            )
        
        # Test invalid final_score
        with pytest.raises(ValueError, match="All scores must be between 0.0 and 1.0"):
            SourceScore(
                url="https://test.com",
                relevance_score=0.5,
                authority_score=0.5,
                freshness_score=0.5,
                final_score=2.0
            )


class TestContentQuality:
    """Test cases for ContentQuality dataclass."""
    
    def test_valid_content_quality_creation(self):
        """Test creating a valid ContentQuality instance."""
        quality = ContentQuality(
            relevance_score=0.85,
            content_length=1500,
            information_density=0.7,
            duplicate_content=False,
            quality_indicators={"readability": 0.8, "structure": 0.9}
        )
        
        assert quality.relevance_score == 0.85
        assert quality.content_length == 1500
        assert quality.information_density == 0.7
        assert quality.duplicate_content is False
        assert quality.quality_indicators == {"readability": 0.8, "structure": 0.9}
    
    def test_content_quality_with_duplicate_content(self):
        """Test ContentQuality with duplicate content flag."""
        quality = ContentQuality(
            relevance_score=0.5,
            content_length=800,
            information_density=0.3,
            duplicate_content=True,
            quality_indicators={}
        )
        
        assert quality.duplicate_content is True
        assert quality.quality_indicators == {}
    
    def test_content_quality_validation(self):
        """Test validation of ContentQuality fields."""
        # Test invalid relevance_score
        with pytest.raises(ValueError, match="relevance_score must be between 0.0 and 1.0"):
            ContentQuality(
                relevance_score=-0.1,
                content_length=1000,
                information_density=0.5,
                duplicate_content=False,
                quality_indicators={}
            )
        
        # Test invalid information_density
        with pytest.raises(ValueError, match="information_density must be between 0.0 and 1.0"):
            ContentQuality(
                relevance_score=0.5,
                content_length=1000,
                information_density=1.5,
                duplicate_content=False,
                quality_indicators={}
            )
        
        # Test invalid content_length
        with pytest.raises(ValueError, match="content_length must be non-negative"):
            ContentQuality(
                relevance_score=0.5,
                content_length=-100,
                information_density=0.5,
                duplicate_content=False,
                quality_indicators={}
            )
    
    def test_content_quality_boundary_values(self):
        """Test ContentQuality with boundary values."""
        # Valid boundary values
        ContentQuality(
            relevance_score=0.0,
            content_length=0,
            information_density=0.0,
            duplicate_content=False,
            quality_indicators={}
        )
        
        ContentQuality(
            relevance_score=1.0,
            content_length=10000,
            information_density=1.0,
            duplicate_content=True,
            quality_indicators={"test": 1.0}
        )


class TestSummaryConfig:
    """Test cases for SummaryConfig dataclass."""
    
    def test_valid_summary_config_creation(self):
        """Test creating a valid SummaryConfig instance."""
        config = SummaryConfig(
            target_length=300,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["technology", "innovation"],
            include_examples=True
        )
        
        assert config.target_length == 300
        assert config.detail_level == DetailLevel.BALANCED
        assert config.focus_areas == ["technology", "innovation"]
        assert config.include_examples is True
    
    def test_summary_config_empty_focus_areas(self):
        """Test SummaryConfig with empty focus areas."""
        config = SummaryConfig(
            target_length=150,
            detail_level=DetailLevel.CONCISE,
            focus_areas=[],
            include_examples=False
        )
        
        assert config.focus_areas == []
        assert config.include_examples is False
    
    def test_summary_config_validation(self):
        """Test validation of SummaryConfig fields."""
        # Test invalid target_length
        with pytest.raises(ValueError, match="target_length must be positive"):
            SummaryConfig(
                target_length=0,
                detail_level=DetailLevel.CONCISE,
                focus_areas=[],
                include_examples=False
            )
        
        with pytest.raises(ValueError, match="target_length must be positive"):
            SummaryConfig(
                target_length=-100,
                detail_level=DetailLevel.CONCISE,
                focus_areas=[],
                include_examples=False
            )


class TestEnhancedSource:
    """Test cases for EnhancedSource model."""
    
    def test_valid_enhanced_source_creation(self):
        """Test creating a valid EnhancedSource instance."""
        source = EnhancedSource(
            url="https://example.com/article",
            title="Test Article",
            main_content="This is the main content of the article with multiple words.",
            images=[{"src": "https://example.com/image.jpg", "alt": "Test image"}],
            categories=["tech", "news"]
        )
        
        assert str(source.url) == "https://example.com/article"
        assert source.title == "Test Article"
        assert source.main_content == "This is the main content of the article with multiple words."
        assert source.images == [{"src": "https://example.com/image.jpg", "alt": "Test image"}]
        assert source.categories == ["tech", "news"]
        
        # Test default values for optional fields
        assert source.content_quality is None
        assert source.scraping_duration is None
        assert source.relevance_score is None
        assert source.word_count is None
        assert source.last_updated is None
    
    def test_enhanced_source_with_optimization_data(self):
        """Test EnhancedSource with optimization data."""
        quality = ContentQuality(
            relevance_score=0.8,
            content_length=1000,
            information_density=0.7,
            duplicate_content=False,
            quality_indicators={}
        )
        
        source = EnhancedSource(
            url="https://example.com/article",
            title="Test Article",
            main_content="Content here",
            images=[],
            categories=["tech"],
            content_quality=quality,
            scraping_duration=2.5,
            relevance_score=0.85,
            word_count=150,
            last_updated=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert source.content_quality == quality
        assert source.scraping_duration == 2.5
        assert source.relevance_score == 0.85
        assert source.word_count == 150
        assert source.last_updated == datetime(2024, 1, 1, 12, 0, 0)
    
    def test_enhanced_source_calculate_word_count(self):
        """Test word count calculation method."""
        source = EnhancedSource(
            url="https://example.com/article",
            title="Test Article",
            main_content="This is a test content with exactly ten words here.",
            images=[],
            categories=[]
        )
        
        # Word count should be calculated and cached
        word_count = source.calculate_word_count()
        assert word_count == 10
        assert source.word_count == 10
        
        # Subsequent calls should return cached value
        assert source.calculate_word_count() == 10
    
    def test_enhanced_source_empty_content(self):
        """Test EnhancedSource with empty content."""
        source = EnhancedSource(
            url="https://example.com/empty",
            title="Empty Article",
            main_content="",
            images=[],
            categories=[]
        )
        
        word_count = source.calculate_word_count()
        assert word_count == 0
        assert source.word_count == 0
    
    def test_enhanced_source_invalid_url(self):
        """Test EnhancedSource with invalid URL."""
        with pytest.raises(ValueError):
            EnhancedSource(
                url="not-a-valid-url",
                title="Test",
                main_content="Content",
                images=[],
                categories=[]
            )