"""
Unit tests for the QueryAnalyzer component.
"""
import pytest
from app.query_analyzer import QueryAnalyzer
from app.optimization_models import QueryComplexity, QueryIntent, SummaryLength


class TestQueryAnalyzer:
    """Test suite for QueryAnalyzer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = QueryAnalyzer()
    
    def test_simple_factual_query(self):
        """Test analysis of simple factual queries."""
        query = "What is Python"
        result = self.analyzer.analyze_query(query)
        
        assert result.complexity == QueryComplexity.SIMPLE
        assert result.intent == QueryIntent.FACTUAL
        assert result.expected_length == SummaryLength.SHORT
        assert result.domain == "technology"
        assert result.recency_importance < 0.5
    
    def test_complex_comparison_query(self):
        """Test analysis of complex comparison queries."""
        query = "Python vs JavaScript for web development: advantages and disadvantages"
        result = self.analyzer.analyze_query(query)
        
        assert result.complexity == QueryComplexity.COMPLEX
        assert result.intent == QueryIntent.COMPARISON
        assert result.expected_length == SummaryLength.LONG
        assert result.domain == "technology"
    
    def test_research_query_moderate_complexity(self):
        """Test analysis of moderate complexity research queries."""
        query = "machine learning impact on healthcare"
        result = self.analyzer.analyze_query(query)
        
        assert result.complexity == QueryComplexity.MODERATE
        assert result.intent == QueryIntent.RESEARCH
        assert result.expected_length == SummaryLength.MEDIUM
        assert result.domain in ["technology", "health"]
    
    def test_howto_query(self):
        """Test analysis of how-to queries."""
        query = "how to setup Docker containers"
        result = self.analyzer.analyze_query(query)
        
        assert result.intent == QueryIntent.HOWTO
        assert result.expected_length == SummaryLength.MEDIUM
        assert result.domain == "technology"
    
    def test_news_query_high_recency(self):
        """Test analysis of news queries with high recency importance."""
        query = "latest AI developments today"
        result = self.analyzer.analyze_query(query)
        
        assert result.intent == QueryIntent.NEWS
        assert result.expected_length == SummaryLength.SHORT
        assert result.recency_importance > 0.5
        assert result.domain == "technology"
    
    def test_domain_detection_health(self):
        """Test domain detection for health-related queries."""
        query = "symptoms of diabetes treatment options"
        result = self.analyzer.analyze_query(query)
        
        assert result.domain == "health"
    
    def test_domain_detection_business(self):
        """Test domain detection for business-related queries."""
        query = "startup investment strategies market analysis"
        result = self.analyzer.analyze_query(query)
        
        assert result.domain == "business"
    
    def test_domain_detection_science(self):
        """Test domain detection for science-related queries."""
        query = "quantum physics research methodology"
        result = self.analyzer.analyze_query(query)
        
        assert result.domain == "science"
    
    def test_domain_detection_education(self):
        """Test domain detection for education-related queries."""
        query = "university course curriculum design"
        result = self.analyzer.analyze_query(query)
        
        assert result.domain == "education"
    
    def test_no_domain_detected(self):
        """Test queries where no specific domain is detected."""
        query = "random general question about stuff"
        result = self.analyzer.analyze_query(query)
        
        assert result.domain is None
    
    def test_complexity_simple_queries(self):
        """Test complexity detection for simple queries."""
        simple_queries = [
            "cats",
            "weather today",
            "pizza recipe"
        ]
        
        for query in simple_queries:
            result = self.analyzer.analyze_query(query)
            assert result.complexity == QueryComplexity.SIMPLE
    
    def test_complexity_moderate_queries(self):
        """Test complexity detection for moderate queries."""
        moderate_queries = [
            "best programming languages for beginners",
            "climate change effects on agriculture",
            "how to learn machine learning"
        ]
        
        for query in moderate_queries:
            result = self.analyzer.analyze_query(query)
            assert result.complexity == QueryComplexity.MODERATE
    
    def test_complexity_complex_queries(self):
        """Test complexity detection for complex queries."""
        complex_queries = [
            "comprehensive analysis of renewable energy implementation strategies and their economic impact",
            "detailed comparison of microservices vs monolithic architecture advantages and disadvantages",
            "thorough evaluation of machine learning frameworks for natural language processing applications"
        ]
        
        for query in complex_queries:
            result = self.analyzer.analyze_query(query)
            assert result.complexity == QueryComplexity.COMPLEX
    
    def test_intent_factual_patterns(self):
        """Test intent detection for factual queries."""
        factual_queries = [
            "What is blockchain technology",
            "Who is the CEO of Tesla",
            "When was Python created",
            "Where is Silicon Valley located",
            "definition of artificial intelligence"
        ]
        
        for query in factual_queries:
            result = self.analyzer.analyze_query(query)
            assert result.intent == QueryIntent.FACTUAL
    
    def test_intent_comparison_patterns(self):
        """Test intent detection for comparison queries."""
        comparison_queries = [
            "React vs Vue.js",
            "iPhone compared to Android",
            "difference between SQL and NoSQL",
            "advantages of cloud computing",
            "pros and cons of remote work"
        ]
        
        for query in comparison_queries:
            result = self.analyzer.analyze_query(query)
            assert result.intent == QueryIntent.COMPARISON
    
    def test_intent_research_patterns(self):
        """Test intent detection for research queries."""
        research_queries = [
            "impact of social media on mental health",
            "why do people procrastinate",
            "what causes climate change",
            "relationship between exercise and productivity"
        ]
        
        for query in research_queries:
            result = self.analyzer.analyze_query(query)
            assert result.intent == QueryIntent.RESEARCH
    
    def test_intent_howto_patterns(self):
        """Test intent detection for how-to queries."""
        howto_queries = [
            "how to build a website",
            "tutorial for React development",
            "guide to machine learning",
            "steps to create a business plan",
            "learn Python programming"
        ]
        
        for query in howto_queries:
            result = self.analyzer.analyze_query(query)
            assert result.intent == QueryIntent.HOWTO
    
    def test_intent_news_patterns(self):
        """Test intent detection for news queries."""
        news_queries = [
            "latest technology news",
            "breaking news about AI",
            "recent developments in healthcare",
            "what happened in the stock market today"
        ]
        
        for query in news_queries:
            result = self.analyzer.analyze_query(query)
            assert result.intent == QueryIntent.NEWS
    
    def test_recency_importance_high(self):
        """Test high recency importance detection."""
        high_recency_queries = [
            "current AI trends today",
            "latest breaking news now",
            "real-time stock updates"
        ]
        
        for query in high_recency_queries:
            result = self.analyzer.analyze_query(query)
            assert result.recency_importance > 0.5
    
    def test_recency_importance_medium(self):
        """Test medium recency importance detection."""
        medium_recency_queries = [
            "this year's technology trends",
            "modern web development practices",
            "2024 market analysis"
        ]
        
        for query in medium_recency_queries:
            result = self.analyzer.analyze_query(query)
            assert 0.2 <= result.recency_importance <= 0.8
    
    def test_recency_importance_low(self):
        """Test low recency importance detection."""
        low_recency_queries = [
            "history of programming languages",
            "ancient civilizations",
            "mathematical theorems"
        ]
        
        for query in low_recency_queries:
            result = self.analyzer.analyze_query(query)
            assert result.recency_importance < 0.5
    
    def test_expected_length_mapping(self):
        """Test expected length determination based on intent and complexity."""
        # Factual queries should be short
        factual_result = self.analyzer.analyze_query("What is Python")
        assert factual_result.expected_length == SummaryLength.SHORT
        
        # Comparison queries should be long
        comparison_result = self.analyzer.analyze_query("Python vs Java comparison")
        assert comparison_result.expected_length == SummaryLength.LONG
        
        # How-to queries should be medium
        howto_result = self.analyzer.analyze_query("how to learn programming")
        assert howto_result.expected_length == SummaryLength.MEDIUM
        
        # News queries should be short
        news_result = self.analyzer.analyze_query("latest tech news")
        assert news_result.expected_length == SummaryLength.SHORT
    
    def test_empty_query(self):
        """Test handling of empty queries."""
        result = self.analyzer.analyze_query("")
        
        assert result.complexity == QueryComplexity.SIMPLE
        assert result.domain is None
        assert result.recency_importance == 0.0
    
    def test_whitespace_handling(self):
        """Test proper handling of queries with extra whitespace."""
        query = "  what is python programming  "
        result = self.analyzer.analyze_query(query)
        
        assert result.intent == QueryIntent.FACTUAL
        assert result.domain == "technology"
    
    def test_case_insensitive_analysis(self):
        """Test that analysis is case-insensitive."""
        queries = [
            "WHAT IS PYTHON",
            "what is python",
            "What Is Python",
            "wHaT iS pYtHoN"
        ]
        
        results = [self.analyzer.analyze_query(q) for q in queries]
        
        # All results should be identical
        for i in range(1, len(results)):
            assert results[i].complexity == results[0].complexity
            assert results[i].intent == results[0].intent
            assert results[i].domain == results[0].domain
            assert results[i].expected_length == results[0].expected_length
    
    def test_multiple_domains_highest_score(self):
        """Test that when multiple domains are detected, the highest scoring one is returned."""
        # Query that could match both technology and business domains
        query = "software company business strategy and programming"
        result = self.analyzer.analyze_query(query)
        
        # Should detect a domain (either technology or business based on keyword frequency)
        assert result.domain is not None
        assert result.domain in ["technology", "business"]
    
    def test_recency_score_capped_at_one(self):
        """Test that recency importance is properly capped at 1.0."""
        # Query with many recency indicators
        query = "today's latest current breaking news now real-time updates 2024"
        result = self.analyzer.analyze_query(query)
        
        assert result.recency_importance <= 1.0
        assert result.recency_importance > 0.8  # Should be high but capped


class TestQueryAnalyzerEdgeCases:
    """Test edge cases and error conditions for QueryAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = QueryAnalyzer()
    
    def test_very_long_query(self):
        """Test analysis of very long queries."""
        long_query = " ".join(["word"] * 100)  # 100-word query
        result = self.analyzer.analyze_query(long_query)
        
        assert result.complexity == QueryComplexity.COMPLEX
        assert isinstance(result.recency_importance, float)
        assert 0.0 <= result.recency_importance <= 1.0
    
    def test_special_characters_query(self):
        """Test queries with special characters."""
        special_query = "what is C++ programming? & how does it work!"
        result = self.analyzer.analyze_query(special_query)
        
        assert result.intent == QueryIntent.FACTUAL
        assert result.domain == "technology"
    
    def test_numeric_query(self):
        """Test queries with numbers."""
        numeric_query = "top 10 programming languages 2024"
        result = self.analyzer.analyze_query(numeric_query)
        
        assert result.domain == "technology"
        assert result.recency_importance > 0.0  # Should detect 2024
    
    def test_mixed_language_patterns(self):
        """Test queries that might have mixed patterns."""
        mixed_query = "how to research the best programming vs scripting languages"
        result = self.analyzer.analyze_query(mixed_query)
        
        # Should prioritize the first matching intent pattern
        assert result.intent in [QueryIntent.HOWTO, QueryIntent.RESEARCH, QueryIntent.COMPARISON]
        assert result.domain == "technology"


if __name__ == "__main__":
    pytest.main([__file__])