"""
Unit tests for AdaptiveSummaryGenerator.
"""
import pytest
from unittest.mock import Mock
from app.adaptive_summary_generator import AdaptiveSummaryGenerator
from app.optimization_models import (
    QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength, 
    DetailLevel, SummaryConfig, EnhancedSource, ContentQuality
)


class TestAdaptiveSummaryGenerator:
    """Test cases for AdaptiveSummaryGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = AdaptiveSummaryGenerator()
    
    def test_initialization(self):
        """Test proper initialization of AdaptiveSummaryGenerator."""
        assert self.generator.length_mappings[SummaryLength.SHORT] == (100, 200)
        assert self.generator.length_mappings[SummaryLength.MEDIUM] == (300, 600)
        assert self.generator.length_mappings[SummaryLength.LONG] == (400, 800)
        
        assert self.generator.detail_level_mappings[QueryComplexity.SIMPLE] == DetailLevel.CONCISE
        assert self.generator.detail_level_mappings[QueryComplexity.MODERATE] == DetailLevel.BALANCED
        assert self.generator.detail_level_mappings[QueryComplexity.COMPLEX] == DetailLevel.COMPREHENSIVE
    
    def test_generate_summary_config_simple_factual(self):
        """Test summary config generation for simple factual queries."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain="tech",
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.3
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert config.target_length == 150  # Average of 100-200
        assert config.detail_level == DetailLevel.CONCISE
        assert "tech" in config.focus_areas
        assert not config.include_examples
    
    def test_generate_summary_config_complex_research(self):
        """Test summary config generation for complex research queries."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.COMPLEX,
            domain="science",
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.LONG,
            recency_importance=0.7
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert config.target_length == 600  # Average of 400-800
        assert config.detail_level == DetailLevel.COMPREHENSIVE
        assert "science" in config.focus_areas
        assert "analysis" in config.focus_areas
        assert "findings" in config.focus_areas
        assert "evidence" in config.focus_areas
        assert config.include_examples
    
    def test_generate_summary_config_comparison_intent(self):
        """Test summary config generation for comparison queries."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain=None,
            intent=QueryIntent.COMPARISON,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.5
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert config.target_length == 450  # Average of 300-600
        assert config.detail_level == DetailLevel.BALANCED
        assert "comparison" in config.focus_areas
        assert "differences" in config.focus_areas
        assert "similarities" in config.focus_areas
        assert not config.include_examples
    
    def test_generate_summary_config_howto_intent(self):
        """Test summary config generation for how-to queries."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain="cooking",
            intent=QueryIntent.HOWTO,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.2
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert config.target_length == 450
        assert config.detail_level == DetailLevel.CONCISE
        assert "cooking" in config.focus_areas
        assert "steps" in config.focus_areas
        assert "process" in config.focus_areas
        assert "instructions" in config.focus_areas
        assert config.include_examples  # How-to queries should include examples
    
    def test_adjust_length_for_content_quality_no_sources(self):
        """Test length adjustment when no sources are available."""
        base_config = SummaryConfig(
            target_length=400,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["tech"],
            include_examples=True
        )
        
        adjusted_config = self.generator.adjust_length_for_content_quality(base_config, [])
        
        assert adjusted_config.target_length == 200  # Half of original, min 50
        assert adjusted_config.detail_level == DetailLevel.CONCISE
        assert adjusted_config.focus_areas == ["tech"]
        assert not adjusted_config.include_examples
    
    def test_adjust_length_for_high_quality_content(self):
        """Test length adjustment for high-quality content."""
        base_config = SummaryConfig(
            target_length=400,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["tech"],
            include_examples=True
        )
        
        # Create high-quality sources
        sources = [
            self._create_enhanced_source("http://example1.com", "High quality content", 0.9, 500),
            self._create_enhanced_source("http://example2.com", "More quality content", 0.85, 600)
        ]
        
        adjusted_config = self.generator.adjust_length_for_content_quality(base_config, sources)
        
        assert adjusted_config.target_length == 480  # 400 * 1.2
        assert adjusted_config.detail_level == DetailLevel.COMPREHENSIVE
        assert adjusted_config.include_examples
    
    def test_adjust_length_for_low_quality_content(self):
        """Test length adjustment for low-quality content."""
        base_config = SummaryConfig(
            target_length=400,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["tech"],
            include_examples=True
        )
        
        # Create low-quality sources
        sources = [
            self._create_enhanced_source("http://example1.com", "Low quality content", 0.3, 200),
            self._create_enhanced_source("http://example2.com", "Poor content", 0.2, 150)
        ]
        
        adjusted_config = self.generator.adjust_length_for_content_quality(base_config, sources)
        
        assert adjusted_config.target_length == 223  # 400 * 0.7 * 0.8 (rounded)
        assert adjusted_config.detail_level == DetailLevel.CONCISE
        assert not adjusted_config.include_examples
    
    def test_create_summary_prompt_concise(self):
        """Test prompt creation for concise summaries."""
        query = "What is Python?"
        sources = [
            self._create_enhanced_source("http://python.org", "Python is a programming language", 0.8, 100)
        ]
        config = SummaryConfig(
            target_length=150,
            detail_level=DetailLevel.CONCISE,
            focus_areas=["programming"],
            include_examples=False
        )
        
        prompt = self.generator.create_summary_prompt(query, sources, config)
        
        assert "What is Python?" in prompt
        assert "approximately 150 words" in prompt
        assert "Concise and direct" in prompt
        assert "programming" in prompt
        assert "Source 1" in prompt
        assert "Python is a programming language" in prompt
    
    def test_create_summary_prompt_comprehensive_with_examples(self):
        """Test prompt creation for comprehensive summaries with examples."""
        query = "How does machine learning work?"
        sources = [
            self._create_enhanced_source("http://ml.com", "Machine learning uses algorithms", 0.9, 300)
        ]
        config = SummaryConfig(
            target_length=600,
            detail_level=DetailLevel.COMPREHENSIVE,
            focus_areas=["algorithms", "data"],
            include_examples=True
        )
        
        prompt = self.generator.create_summary_prompt(query, sources, config)
        
        assert "How does machine learning work?" in prompt
        assert "approximately 600 words" in prompt
        assert "Comprehensive analysis" in prompt
        assert "algorithms, data" in prompt
        assert "Include specific examples" in prompt
    
    def test_generate_summary_integration(self):
        """Test complete summary generation integration."""
        query = "Benefits of renewable energy"
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain="energy",
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.6
        )
        sources = [
            self._create_enhanced_source(
                "http://energy.gov", 
                "Renewable energy sources like solar and wind power provide clean electricity. "
                "They reduce carbon emissions and help combat climate change. "
                "Solar panels convert sunlight into electricity efficiently.",
                0.8, 
                200
            )
        ]
        
        summary = self.generator.generate_summary(query, sources, query_analysis)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "renewable energy" in summary.lower() or "solar" in summary.lower()
    
    def test_fallback_summary_no_sources(self):
        """Test fallback summary generation when no sources available."""
        query = "Test query"
        config = SummaryConfig(
            target_length=200,
            detail_level=DetailLevel.CONCISE,
            focus_areas=[],
            include_examples=False
        )
        
        summary = self.generator._generate_fallback_summary(query, [], config)
        
        assert "No relevant sources found" in summary
        assert "Test query" in summary
    
    def test_extract_sentences(self):
        """Test sentence extraction from text."""
        text = "This is sentence one. This is sentence two! Is this sentence three? Short."
        
        sentences = self.generator._extract_sentences(text)
        
        assert len(sentences) == 3  # "Short" should be filtered out (too short)
        assert "This is sentence one" in sentences
        assert "This is sentence two" in sentences
        assert "Is this sentence three" in sentences
    
    def test_score_sentences(self):
        """Test sentence scoring based on query relevance."""
        sentences = [
            "Python is a programming language",
            "Java is also a programming language", 
            "The weather is nice today"
        ]
        query = "Python programming"
        
        scored_sentences = self.generator._score_sentences(sentences, query)
        
        assert len(scored_sentences) == 3
        # First sentence should have highest score (contains both "Python" and "programming")
        assert scored_sentences[0][1] == 1.0  # 2/2 words match
        # Second sentence should have medium score (contains "programming")
        assert scored_sentences[1][1] == 0.5  # 1/2 words match
        # Third sentence should have lowest score (no matches)
        assert scored_sentences[2][1] == 0.0  # 0/2 words match
    
    def test_fallback_summary_with_sources(self):
        """Test fallback summary generation with actual sources."""
        query = "machine learning algorithms"
        sources = [
            self._create_enhanced_source(
                "http://ml.com",
                "Machine learning algorithms are powerful tools. "
                "They can process large datasets efficiently. "
                "Neural networks are a type of machine learning algorithm. "
                "Random forests are another popular algorithm type.",
                0.8,
                300
            )
        ]
        config = SummaryConfig(
            target_length=100,
            detail_level=DetailLevel.CONCISE,
            focus_areas=["algorithms"],
            include_examples=False
        )
        
        summary = self.generator._generate_fallback_summary(query, sources, config)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Should contain relevant content
        assert any(word in summary.lower() for word in ["machine", "learning", "algorithm"])
    
    def _create_enhanced_source(self, url: str, content: str, relevance: float, word_count: int) -> EnhancedSource:
        """Helper method to create EnhancedSource for testing."""
        content_quality = ContentQuality(
            relevance_score=relevance,
            content_length=len(content),
            information_density=0.7,
            duplicate_content=False,
            quality_indicators={"readability": 0.8}
        )
        
        return EnhancedSource(
            url=url,
            title="Test Title",
            main_content=content,
            images=[],
            categories=["test"],
            content_quality=content_quality,
            word_count=word_count,
            relevance_score=relevance
        )


class TestSummaryConfigGeneration:
    """Test cases for summary configuration generation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = AdaptiveSummaryGenerator()
    
    def test_news_intent_focus_areas(self):
        """Test focus areas for news intent queries."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain="politics",
            intent=QueryIntent.NEWS,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.9
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert "politics" in config.focus_areas
        assert "recent" in config.focus_areas
        assert "updates" in config.focus_areas
        assert "developments" in config.focus_areas
    
    def test_no_domain_specified(self):
        """Test config generation when no domain is specified."""
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain=None,
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.4
        )
        
        config = self.generator.generate_summary_config(query_analysis)
        
        assert config.target_length == 450
        assert config.detail_level == DetailLevel.BALANCED
        # Should not crash with None domain
        assert isinstance(config.focus_areas, list)


class TestContentQualityAdjustments:
    """Test cases for content quality-based adjustments."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = AdaptiveSummaryGenerator()
    
    def test_insufficient_content_length_adjustment(self):
        """Test adjustment when total content is insufficient."""
        base_config = SummaryConfig(
            target_length=500,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["tech"],
            include_examples=True
        )
        
        # Create sources with insufficient total content (less than 2x target)
        sources = [
            self._create_enhanced_source("http://example.com", "Short content", 0.7, 200)
        ]
        
        adjusted_config = self.generator.adjust_length_for_content_quality(base_config, sources)
        
        # Should be reduced due to insufficient content (500 * 1.0 * 0.8 = 400)
        assert adjusted_config.target_length == 400
    
    def test_mixed_quality_sources(self):
        """Test adjustment with mixed quality sources."""
        base_config = SummaryConfig(
            target_length=400,
            detail_level=DetailLevel.BALANCED,
            focus_areas=["tech"],
            include_examples=True
        )
        
        sources = [
            self._create_enhanced_source("http://high.com", "High quality", 0.9, 300),
            self._create_enhanced_source("http://low.com", "Low quality", 0.3, 200)
        ]
        
        adjusted_config = self.generator.adjust_length_for_content_quality(base_config, sources)
        
        # Average quality is 0.6, with insufficient content (500 total < 800 needed)
        # Should be 400 * 1.0 * 0.8 = 320
        assert adjusted_config.target_length == 320
        assert adjusted_config.detail_level == DetailLevel.BALANCED
    
    def _create_enhanced_source(self, url: str, content: str, relevance: float, word_count: int) -> EnhancedSource:
        """Helper method to create EnhancedSource for testing."""
        content_quality = ContentQuality(
            relevance_score=relevance,
            content_length=len(content),
            information_density=0.7,
            duplicate_content=False,
            quality_indicators={"readability": 0.8}
        )
        
        return EnhancedSource(
            url=url,
            title="Test Title",
            main_content=content,
            images=[],
            categories=["test"],
            content_quality=content_quality,
            word_count=word_count,
            relevance_score=relevance
        )