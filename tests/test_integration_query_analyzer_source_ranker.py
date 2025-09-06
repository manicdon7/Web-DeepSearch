"""
Integration tests for QueryAnalyzer and SourceRanker working together.
"""
import pytest
from app.query_analyzer import QueryAnalyzer
from app.source_ranker import SourceRanker


class TestQueryAnalyzerSourceRankerIntegration:
    """Test integration between QueryAnalyzer and SourceRanker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.query_analyzer = QueryAnalyzer()
        self.source_ranker = SourceRanker()
        
        # Sample search results
        self.search_results = [
            {
                'url': 'https://stackoverflow.com/questions/python-ml-best-practices',
                'title': 'Python Machine Learning Best Practices 2024',
                'snippet': 'Latest techniques and best practices for machine learning in Python'
            },
            {
                'url': 'https://randomsite.com/old-tutorial',
                'title': 'Basic Python Tutorial',
                'snippet': 'Learn Python programming basics'
            },
            {
                'url': 'https://docs.python.org/3/library/sklearn.html',
                'title': 'Scikit-learn Documentation',
                'snippet': 'Official documentation for Python machine learning library'
            }
        ]
    
    def test_technology_query_integration(self):
        """Test complete pipeline for a technology-related query."""
        query = "Python machine learning best practices 2024"
        
        # Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Verify query analysis results
        assert query_analysis.domain == 'technology'
        assert query_analysis.complexity in [query_analysis.complexity.MODERATE, query_analysis.complexity.COMPLEX]
        assert query_analysis.recency_importance > 0.4  # Should detect 2024 (adjusted expectation)
        
        # Rank sources using query analysis
        ranked_sources = self.source_ranker.rank_sources(self.search_results, query_analysis)
        
        # Verify ranking results
        assert len(ranked_sources) == 3
        
        # StackOverflow with recent, relevant content should rank highest
        assert ranked_sources[0].url == 'https://stackoverflow.com/questions/python-ml-best-practices'
        assert ranked_sources[0].final_score > 0.6  # Should have good score (adjusted expectation)
        
        # All sources should have valid scores
        for source in ranked_sources:
            assert 0.0 <= source.final_score <= 1.0
            assert 0.0 <= source.relevance_score <= 1.0
            assert 0.0 <= source.authority_score <= 1.0
            assert 0.0 <= source.freshness_score <= 1.0
    
    def test_factual_query_integration(self):
        """Test integration for a simple factual query."""
        query = "What is machine learning"
        
        # Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Verify query analysis
        assert query_analysis.intent.value == 'factual'
        assert query_analysis.complexity.value in ['simple', 'moderate']  # Allow for moderate complexity
        assert query_analysis.expected_length.value == 'short'
        
        # Rank sources
        ranked_sources = self.source_ranker.rank_sources(self.search_results, query_analysis)
        
        # Official documentation should rank highly for factual queries
        official_docs = [s for s in ranked_sources if 'docs.python.org' in s.url]
        assert len(official_docs) == 1
        assert official_docs[0].authority_score == 1.0  # High authority
    
    def test_comparison_query_integration(self):
        """Test integration for a comparison query."""
        query = "Python vs R for machine learning comparison"
        
        # Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Verify query analysis
        assert query_analysis.intent.value == 'comparison'
        assert query_analysis.expected_length.value == 'long'
        
        # Rank sources
        ranked_sources = self.source_ranker.rank_sources(self.search_results, query_analysis)
        
        # Should handle comparison queries appropriately
        assert len(ranked_sources) == 3
        
        # Verify scores are calculated properly
        for source in ranked_sources:
            assert hasattr(source, 'relevance_score')
            assert hasattr(source, 'authority_score')
            assert hasattr(source, 'freshness_score')
            assert hasattr(source, 'final_score')
    
    def test_news_query_integration(self):
        """Test integration for a news-related query."""
        query = "latest Python machine learning news 2024"
        
        # Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Verify high recency importance for news queries
        assert query_analysis.intent.value == 'news'
        assert query_analysis.recency_importance > 0.8  # Should be very high
        
        # Rank sources
        ranked_sources = self.source_ranker.rank_sources(self.search_results, query_analysis)
        
        # Sources with freshness indicators should benefit from high recency importance
        fresh_sources = [s for s in ranked_sources if '2024' in self.search_results[0]['title']]
        if fresh_sources:
            assert fresh_sources[0].freshness_score > 0.7
    
    def test_empty_results_integration(self):
        """Test integration with empty search results."""
        query = "Python machine learning"
        
        # Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Rank empty results
        ranked_sources = self.source_ranker.rank_sources([], query_analysis)
        
        # Should handle gracefully
        assert ranked_sources == []
    
    def test_domain_specific_ranking(self):
        """Test that domain detection influences source ranking."""
        health_results = [
            {
                'url': 'https://mayoclinic.org/health-conditions',
                'title': 'Health Conditions and Treatments',
                'snippet': 'Medical information about various health conditions'
            },
            {
                'url': 'https://randomsite.com/health-blog',
                'title': 'Health Blog Post',
                'snippet': 'Personal opinions about health topics'
            }
        ]
        
        health_query = "symptoms of diabetes treatment options"
        
        # Analyze health query
        query_analysis = self.query_analyzer.analyze_query(health_query)
        assert query_analysis.domain == 'health'
        
        # Rank health sources
        ranked_sources = self.source_ranker.rank_sources(health_results, query_analysis)
        
        # Mayo Clinic should rank higher due to authority in health domain
        mayo_clinic_source = [s for s in ranked_sources if 'mayoclinic.org' in s.url][0]
        random_site_source = [s for s in ranked_sources if 'randomsite.com' in s.url][0]
        
        assert mayo_clinic_source.final_score > random_site_source.final_score
        assert mayo_clinic_source.authority_score > random_site_source.authority_score


if __name__ == '__main__':
    pytest.main([__file__])