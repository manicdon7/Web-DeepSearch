"""
Unit tests for the SourceRanker class.
"""
import pytest
from app.source_ranker import SourceRanker
from app.optimization_models import QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength


class TestSourceRanker:
    """Test cases for SourceRanker functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ranker = SourceRanker()
        
        # Sample search results for testing
        self.sample_results = [
            {
                'url': 'https://stackoverflow.com/questions/python-best-practices',
                'title': 'Python Best Practices for Machine Learning',
                'snippet': 'Comprehensive guide to Python programming best practices for ML projects'
            },
            {
                'url': 'https://example.com/blog/post/123?utm_source=google&ref=search',
                'title': 'Random Blog Post',
                'snippet': 'Some random content about various topics'
            },
            {
                'url': 'https://docs.python.org/3/tutorial/',
                'title': 'Python Tutorial - Official Documentation',
                'snippet': 'The official Python tutorial covering language fundamentals'
            },
            {
                'url': 'https://cnn.com/2024/tech-news-latest',
                'title': 'Latest Technology News 2024',
                'snippet': 'Breaking news about recent developments in technology sector'
            }
        ]
        
        # Sample query analysis
        self.tech_query_analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain='technology',
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.6
        )
    
    def test_rank_sources_basic_functionality(self):
        """Test basic source ranking functionality."""
        ranked_sources = self.ranker.rank_sources(self.sample_results, self.tech_query_analysis)
        
        # Should return same number of sources
        assert len(ranked_sources) == len(self.sample_results)
        
        # Should be sorted by final_score (highest first)
        for i in range(len(ranked_sources) - 1):
            assert ranked_sources[i].final_score >= ranked_sources[i + 1].final_score
        
        # All scores should be between 0 and 1
        for source in ranked_sources:
            assert 0.0 <= source.relevance_score <= 1.0
            assert 0.0 <= source.authority_score <= 1.0
            assert 0.0 <= source.freshness_score <= 1.0
            assert 0.0 <= source.final_score <= 1.0
    
    def test_authority_scoring_high_quality_domains(self):
        """Test authority scoring for known high-quality domains."""
        # Test high authority domain
        stackoverflow_score = self.ranker._calculate_authority_score('https://stackoverflow.com/questions/123')
        assert stackoverflow_score == 1.0
        
        # Test government domain (cdc.gov is in high authority list, so it gets 1.0)
        gov_score = self.ranker._calculate_authority_score('https://cdc.gov/health-info')
        assert gov_score == 1.0
        
        # Test education domain
        edu_score = self.ranker._calculate_authority_score('https://mit.edu/research')
        assert edu_score == 0.9
        
        # Test organization domain
        org_score = self.ranker._calculate_authority_score('https://mozilla.org/docs')
        assert org_score == 1.0  # Mozilla is in high authority list
        
        # Test unknown domain
        unknown_score = self.ranker._calculate_authority_score('https://randomsite.com/page')
        assert unknown_score == 0.3
    
    def test_authority_scoring_subdomains(self):
        """Test authority scoring for subdomains of known domains."""
        # Test subdomain of high authority domain
        subdomain_score = self.ranker._calculate_authority_score('https://blog.stackoverflow.com/post')
        assert subdomain_score == 0.8
        
        # Test www prefix removal
        www_score = self.ranker._calculate_authority_score('https://www.github.com/repo')
        assert www_score == 1.0
    
    def test_url_quality_scoring(self):
        """Test URL structure quality assessment."""
        # Test clean, short URL
        clean_score = self.ranker._calculate_url_quality_score('https://example.com/article/title')
        
        # Test URL with many parameters
        messy_score = self.ranker._calculate_url_quality_score(
            'https://example.com/page?id=123&sessionid=abc&utm_source=google&ref=search&tracking=true'
        )
        
        # Test very deep URL
        deep_score = self.ranker._calculate_url_quality_score(
            'https://example.com/category/subcategory/item/details/page/section'
        )
        
        # Clean URL should score higher than messy or deep URLs
        assert clean_score > messy_score
        assert clean_score > deep_score
    
    def test_relevance_scoring_with_domain_keywords(self):
        """Test relevance scoring based on domain-specific keywords."""
        title = "Python Machine Learning Tutorial"
        snippet = "Learn AI and programming with this comprehensive guide"
        
        relevance_score = self.ranker._calculate_relevance_score(
            title, snippet, self.tech_query_analysis
        )
        
        # Should have reasonable relevance due to tech keywords (adjusted expectation)
        assert relevance_score > 0.4
    
    def test_relevance_scoring_title_boost(self):
        """Test that title matches get boosted in relevance scoring."""
        # Title with relevant keywords
        title_match = "Python Programming Guide"
        snippet_generic = "Some general content here"
        
        # Generic title but relevant snippet
        title_generic = "General Guide"
        snippet_match = "Python programming and software development"
        
        score_title_match = self.ranker._calculate_relevance_score(
            title_match, snippet_generic, self.tech_query_analysis
        )
        score_snippet_match = self.ranker._calculate_relevance_score(
            title_generic, snippet_match, self.tech_query_analysis
        )
        
        # Title matches should get higher scores due to title boost
        assert score_title_match >= score_snippet_match
    
    def test_freshness_scoring_with_recency_importance(self):
        """Test freshness scoring adjusts based on query recency importance."""
        url = "https://example.com/article"
        title = "Latest Technology Trends 2024"
        snippet = "Recent developments in the tech industry"
        
        # High recency importance query
        high_recency_query = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain='technology',
            intent=QueryIntent.NEWS,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.9
        )
        
        # Low recency importance query
        low_recency_query = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain='technology',
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.2
        )
        
        high_recency_score = self.ranker._calculate_freshness_score(
            url, title, snippet, high_recency_query
        )
        low_recency_score = self.ranker._calculate_freshness_score(
            url, title, snippet, low_recency_query
        )
        
        # High recency importance should boost freshness score
        assert high_recency_score >= low_recency_score
    
    def test_freshness_scoring_date_indicators(self):
        """Test freshness scoring detects date indicators."""
        url = "https://example.com/2024/article"
        title = "Updated Guide January 2024"
        snippet = "Latest information about current trends"
        
        freshness_score = self.ranker._calculate_freshness_score(
            url, title, snippet, self.tech_query_analysis
        )
        
        # Should have high freshness due to 2024 and "latest" keywords
        assert freshness_score > 0.7
    
    def test_domain_keywords_mapping(self):
        """Test domain keyword mapping functionality."""
        tech_keywords = self.ranker._get_domain_keywords('technology')
        health_keywords = self.ranker._get_domain_keywords('health')
        unknown_keywords = self.ranker._get_domain_keywords('unknown_domain')
        
        assert 'tech' in tech_keywords
        assert 'programming' in tech_keywords
        assert 'health' in health_keywords
        assert 'medical' in health_keywords
        assert unknown_keywords == []
    
    def test_intent_keywords_mapping(self):
        """Test intent keyword mapping functionality."""
        factual_keywords = self.ranker._get_intent_keywords(QueryIntent.FACTUAL)
        comparison_keywords = self.ranker._get_intent_keywords(QueryIntent.COMPARISON)
        howto_keywords = self.ranker._get_intent_keywords(QueryIntent.HOWTO)
        
        assert 'what' in factual_keywords
        assert 'definition' in factual_keywords
        assert 'vs' in comparison_keywords
        assert 'compare' in comparison_keywords
        assert 'how' in howto_keywords
        assert 'tutorial' in howto_keywords
    
    def test_empty_search_results(self):
        """Test handling of empty search results."""
        ranked_sources = self.ranker.rank_sources([], self.tech_query_analysis)
        assert ranked_sources == []
    
    def test_malformed_urls(self):
        """Test handling of malformed URLs."""
        malformed_results = [
            {
                'url': 'not-a-valid-url',
                'title': 'Test Title',
                'snippet': 'Test snippet'
            },
            {
                'url': '',
                'title': 'Empty URL',
                'snippet': 'Test snippet'
            }
        ]
        
        ranked_sources = self.ranker.rank_sources(malformed_results, self.tech_query_analysis)
        
        # Should handle gracefully without crashing
        assert len(ranked_sources) == 2
        
        # Malformed URLs should get low authority scores
        for source in ranked_sources:
            assert source.authority_score <= 0.3
    
    def test_missing_title_and_snippet(self):
        """Test handling of missing title and snippet data."""
        incomplete_results = [
            {
                'url': 'https://example.com/page1',
                'title': '',
                'snippet': ''
            },
            {
                'url': 'https://example.com/page2'
                # Missing title and snippet keys
            }
        ]
        
        ranked_sources = self.ranker.rank_sources(incomplete_results, self.tech_query_analysis)
        
        # Should handle gracefully
        assert len(ranked_sources) == 2
        
        # Missing content should result in low relevance scores
        for source in ranked_sources:
            assert source.relevance_score <= 0.5
    
    def test_scoring_weights_sum_to_one(self):
        """Test that scoring weights sum to approximately 1.0."""
        weights = self.ranker.scoring_weights
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point errors
    
    def test_comprehensive_ranking_scenario(self):
        """Test a comprehensive ranking scenario with diverse sources."""
        diverse_results = [
            {
                'url': 'https://stackoverflow.com/questions/python-ml-2024',
                'title': 'Python Machine Learning Best Practices 2024',
                'snippet': 'Latest techniques for AI and machine learning in Python programming'
            },
            {
                'url': 'https://randomsite.com/old-post/2020/python-basics?id=123&tracking=true',
                'title': 'Basic Python Tutorial',
                'snippet': 'Old tutorial about Python basics from 2020'
            },
            {
                'url': 'https://docs.python.org/3/library/ml.html',
                'title': 'Python ML Library Documentation',
                'snippet': 'Official documentation for Python machine learning libraries'
            }
        ]
        
        ranked_sources = self.ranker.rank_sources(diverse_results, self.tech_query_analysis)
        
        # StackOverflow with recent, relevant content should rank highest
        assert ranked_sources[0].url == 'https://stackoverflow.com/questions/python-ml-2024'
        
        # Official docs should rank second (high authority, good relevance)
        assert ranked_sources[1].url == 'https://docs.python.org/3/library/ml.html'
        
        # Random site with old content should rank lowest
        assert ranked_sources[2].url == 'https://randomsite.com/old-post/2020/python-basics?id=123&tracking=true'
        
        # Verify score progression
        assert ranked_sources[0].final_score > ranked_sources[1].final_score
        assert ranked_sources[1].final_score > ranked_sources[2].final_score


if __name__ == '__main__':
    pytest.main([__file__])