"""
Integration tests for the optimized search client with intelligent source selection.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime

from app.search_client import OptimizedSearchClient, search_and_scrape_multiple_sources
from app.optimization_models import (
    QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength,
    SourceScore, ScrapingResult, ContentQuality, EnhancedSource
)


class TestOptimizedSearchClient:
    """Test suite for OptimizedSearchClient."""
    
    @pytest.fixture
    def client(self):
        """Create an OptimizedSearchClient instance for testing."""
        return OptimizedSearchClient(
            max_concurrent=3,
            timeout_per_source=5,
            max_sources=10,
            enable_early_termination=True
        )
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock search results from DuckDuckGo."""
        return [
            {
                'href': 'https://example.com/article1',
                'title': 'Python Programming Guide',
                'body': 'Learn Python programming with this comprehensive guide'
            },
            {
                'href': 'https://docs.python.org/tutorial',
                'title': 'Python Tutorial',
                'body': 'Official Python tutorial and documentation'
            },
            {
                'href': 'https://stackoverflow.com/questions/python',
                'title': 'Python Questions',
                'body': 'Common Python programming questions and answers'
            }
        ]
    
    @pytest.fixture
    def mock_query_analysis(self):
        """Mock query analysis result."""
        return QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain='technology',
            intent=QueryIntent.HOWTO,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.3
        )
    
    @pytest.fixture
    def mock_ranked_sources(self):
        """Mock ranked source scores."""
        return [
            SourceScore(
                url='https://docs.python.org/tutorial',
                relevance_score=0.9,
                authority_score=1.0,
                freshness_score=0.7,
                final_score=0.9
            ),
            SourceScore(
                url='https://stackoverflow.com/questions/python',
                relevance_score=0.8,
                authority_score=0.8,
                freshness_score=0.6,
                final_score=0.75
            ),
            SourceScore(
                url='https://example.com/article1',
                relevance_score=0.7,
                authority_score=0.3,
                freshness_score=0.8,
                final_score=0.6
            )
        ]
    
    @pytest.fixture
    def mock_scraping_results(self):
        """Mock scraping results."""
        return [
            ScrapingResult(
                url='https://docs.python.org/tutorial',
                success=True,
                content={
                    'url': 'https://docs.python.org/tutorial',
                    'title': 'Python Tutorial',
                    'main_content': 'Python is a programming language that lets you work quickly and integrate systems more effectively. This tutorial introduces the reader informally to the basic concepts and features of the Python language and system.',
                    'images': [],
                    'categories': ['programming', 'tutorial']
                },
                duration=2.5
            ),
            ScrapingResult(
                url='https://stackoverflow.com/questions/python',
                success=True,
                content={
                    'url': 'https://stackoverflow.com/questions/python',
                    'title': 'Python Questions',
                    'main_content': 'Stack Overflow is a question and answer site for professional and enthusiast programmers. Here you can find answers to common Python programming questions.',
                    'images': [],
                    'categories': ['programming', 'qa']
                },
                duration=3.2
            ),
            ScrapingResult(
                url='https://example.com/article1',
                success=False,
                error='Timeout after 5s',
                duration=5.0
            )
        ]
    
    def test_initialization(self, client):
        """Test that OptimizedSearchClient initializes correctly."""
        assert client.max_sources == 10
        assert client.enable_early_termination is True
        assert client.query_analyzer is not None
        assert client.source_ranker is not None
        assert client.content_quality_assessor is not None
        assert client.cache_manager is not None
        assert client.concurrent_scraper is not None
    
    @patch('app.search_client.DDGS')
    def test_perform_web_search(self, mock_ddgs, client, mock_search_results):
        """Test web search functionality."""
        # Setup mock
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_search_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Execute
        results = client._perform_web_search("python programming")
        
        # Verify
        assert len(results) == 3
        assert results[0]['url'] == 'https://example.com/article1'
        assert results[0]['title'] == 'Python Programming Guide'
        assert results[0]['snippet'] == 'Learn Python programming with this comprehensive guide'
    
    def test_filter_blocked_domains(self, client):
        """Test filtering of blocked domains."""
        search_results = [
            {'url': 'https://example.com/article', 'title': 'Good Article'},
            {'url': 'https://youtube.com/watch?v=123', 'title': 'Video'},
            {'url': 'https://stackoverflow.com/questions', 'title': 'Question'},
            {'url': 'https://instagram.com/post', 'title': 'Social Post'}
        ]
        
        filtered = client._filter_blocked_domains(search_results)
        
        assert len(filtered) == 2
        assert filtered[0]['url'] == 'https://example.com/article'
        assert filtered[1]['url'] == 'https://stackoverflow.com/questions'
    
    def test_check_cache_with_cached_content(self, client, mock_ranked_sources):
        """Test cache checking when content is cached."""
        # Setup cache with one item
        enhanced_source = EnhancedSource(
            url='https://docs.python.org/tutorial',
            title='Python Tutorial',
            main_content='Cached content about Python',
            images=[],
            categories=['programming']
        )
        client.cache_manager.cache_content(enhanced_source, "python tutorial")
        
        # Execute
        cached, to_scrape = client._check_cache(mock_ranked_sources, "python tutorial")
        
        # Verify
        assert len(cached) == 1
        assert len(to_scrape) == 2
        assert str(cached[0]['url']) == 'https://docs.python.org/tutorial'
        assert cached[0]['main_content'] == 'Cached content about Python'
    
    def test_check_cache_no_cached_content(self, client, mock_ranked_sources):
        """Test cache checking when no content is cached."""
        cached, to_scrape = client._check_cache(mock_ranked_sources, "python tutorial")
        
        assert len(cached) == 0
        assert len(to_scrape) == 3
    
    def test_process_scraping_results(self, client, mock_scraping_results, mock_query_analysis):
        """Test processing of scraping results with quality assessment."""
        # Mock content quality assessor
        mock_quality = ContentQuality(
            relevance_score=0.8,
            content_length=150,
            information_density=0.6,
            duplicate_content=False,
            quality_indicators={'structure_score': 0.7}
        )
        client.content_quality_assessor.assess_content = Mock(return_value=mock_quality)
        
        # Execute
        successful = client._process_scraping_results(
            mock_scraping_results, "python tutorial", mock_query_analysis
        )
        
        # Verify
        assert len(successful) == 2  # Two successful scraping results
        assert successful[0]['title'] == 'Python Tutorial'
        assert successful[1]['title'] == 'Python Questions'
        
        # Verify content was cached
        cached_content = client.cache_manager.get_cached_content(
            'https://docs.python.org/tutorial', "python tutorial"
        )
        assert cached_content is not None
    
    def test_process_scraping_results_low_quality_filtered(self, client, mock_scraping_results, mock_query_analysis):
        """Test that low-quality content is filtered out."""
        # Mock low-quality assessment
        mock_quality = ContentQuality(
            relevance_score=0.1,  # Low relevance
            content_length=20,    # Short content
            information_density=0.1,  # Low density
            duplicate_content=False,
            quality_indicators={'structure_score': 0.2}
        )
        client.content_quality_assessor.assess_content = Mock(return_value=mock_quality)
        
        # Execute
        successful = client._process_scraping_results(
            mock_scraping_results, "python tutorial", mock_query_analysis
        )
        
        # Verify all content was filtered out due to low quality
        assert len(successful) == 0
    
    def test_apply_stopping_criteria_simple_query(self, client):
        """Test stopping criteria for simple queries."""
        # Create mock query analysis for simple query
        simple_query = QueryAnalysis(
            complexity=QueryComplexity.SIMPLE,
            domain='technology',
            intent=QueryIntent.FACTUAL,
            expected_length=SummaryLength.SHORT,
            recency_importance=0.2
        )
        
        # Create 10 mock sources
        sources = [{'url': f'https://example{i}.com', 'title': f'Article {i}'} 
                  for i in range(10)]
        
        # Execute
        filtered = client._apply_stopping_criteria(sources, simple_query)
        
        # Verify limited to 5 sources for simple queries
        assert len(filtered) == 5
    
    def test_apply_stopping_criteria_complex_query(self, client):
        """Test stopping criteria for complex queries."""
        # Create mock query analysis for complex query
        complex_query = QueryAnalysis(
            complexity=QueryComplexity.COMPLEX,
            domain='technology',
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.LONG,
            recency_importance=0.8
        )
        
        # Create 15 mock sources
        sources = [{'url': f'https://example{i}.com', 'title': f'Article {i}'} 
                  for i in range(15)]
        
        # Execute
        filtered = client._apply_stopping_criteria(sources, complex_query)
        
        # Verify limited to 12 sources for complex queries
        assert len(filtered) == 12
    
    @patch('app.search_client.DDGS')
    @patch('asyncio.run')
    def test_full_search_integration(self, mock_asyncio_run, mock_ddgs, client, 
                                   mock_search_results, mock_scraping_results):
        """Test full search integration with all components."""
        # Setup mocks
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_search_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Mock asyncio.run to return scraping results
        mock_asyncio_run.return_value = mock_scraping_results
        
        # Mock content quality assessor
        mock_quality = ContentQuality(
            relevance_score=0.8,
            content_length=150,
            information_density=0.6,
            duplicate_content=False,
            quality_indicators={'structure_score': 0.7}
        )
        client.content_quality_assessor.assess_content = Mock(return_value=mock_quality)
        
        # Execute
        results = client.search_and_scrape_multiple_sources("python programming tutorial")
        
        # Verify
        assert len(results) == 2  # Two successful results
        assert results[0]['title'] == 'Python Tutorial'
        assert results[1]['title'] == 'Python Questions'
        
        # Verify components were called
        mock_asyncio_run.assert_called_once()
    
    @patch('app.search_client.DDGS')
    def test_search_with_no_results(self, mock_ddgs, client):
        """Test search behavior when no results are found."""
        # Setup mock to return empty results
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Execute
        results = client.search_and_scrape_multiple_sources("nonexistent query")
        
        # Verify
        assert results == []
    
    @patch('app.search_client.DDGS')
    def test_search_with_exception_fallback(self, mock_ddgs, client):
        """Test fallback behavior when optimization fails."""
        # Setup mock to raise exception during web search
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.side_effect = Exception("Search API error")
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Execute - this should trigger the fallback due to the exception
        results = client.search_and_scrape_multiple_sources("test query")
        
        # Verify fallback behavior (empty results when search fails)
        assert results == []
    
    def test_get_cache_statistics(self, client):
        """Test cache statistics retrieval."""
        stats = client.get_cache_statistics()
        
        assert 'size' in stats
        assert 'max_size' in stats
        assert 'statistics' in stats
        assert 'hit_rate' in stats['statistics']
    
    def test_clear_cache(self, client):
        """Test cache clearing functionality."""
        # Add some content to cache
        enhanced_source = EnhancedSource(
            url='https://example.com',
            title='Test',
            main_content='Test content',
            images=[],
            categories=[]
        )
        client.cache_manager.cache_content(enhanced_source, "test")
        
        # Clear cache
        cleared_count = client.clear_cache()
        
        assert cleared_count == 1
        
        # Verify cache is empty
        stats = client.get_cache_statistics()
        assert stats['size'] == 0


class TestLegacySearchFunction:
    """Test suite for the legacy search function."""
    
    @patch('app.search_client.DDGS')
    @patch('app.scraper.scrape_url')
    def test_legacy_search_function(self, mock_scrape_url, mock_ddgs):
        """Test the legacy search function for backward compatibility."""
        # Setup mocks
        mock_search_results = [
            {'href': 'https://example.com/article', 'title': 'Test Article', 'body': 'Test content'}
        ]
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_search_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        mock_scrape_url.return_value = {
            'url': 'https://example.com/article',
            'title': 'Test Article',
            'main_content': 'This is test content for the article.',
            'images': [],
            'categories': []
        }
        
        # Execute
        results = search_and_scrape_multiple_sources("test query")
        
        # Verify
        assert len(results) == 1
        assert results[0]['title'] == 'Test Article'
        assert results[0]['main_content'] == 'This is test content for the article.'
        
        # Verify scraper was called
        mock_scrape_url.assert_called_once_with('https://example.com/article')
    
    @patch('app.search_client.DDGS')
    @patch('app.scraper.scrape_url')
    def test_legacy_search_filters_blocked_domains(self, mock_scrape_url, mock_ddgs):
        """Test that legacy function still filters blocked domains."""
        # Setup mocks with blocked domain
        mock_search_results = [
            {'href': 'https://youtube.com/watch', 'title': 'Video', 'body': 'Video content'},
            {'href': 'https://example.com/article', 'title': 'Article', 'body': 'Article content'}
        ]
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_search_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        mock_scrape_url.return_value = {
            'url': 'https://example.com/article',
            'title': 'Article',
            'main_content': 'Article content',
            'images': [],
            'categories': []
        }
        
        # Execute
        results = search_and_scrape_multiple_sources("test query")
        
        # Verify only non-blocked domain was scraped
        assert len(results) == 1
        assert results[0]['url'] == 'https://example.com/article'
        mock_scrape_url.assert_called_once_with('https://example.com/article')
    
    @patch('app.search_client.DDGS')
    def test_legacy_search_no_results(self, mock_ddgs):
        """Test legacy function with no search results."""
        # Setup mock to return empty results
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Execute
        results = search_and_scrape_multiple_sources("nonexistent query")
        
        # Verify
        assert results == []
    
    @patch('app.search_client.DDGS')
    def test_legacy_search_exception_handling(self, mock_ddgs):
        """Test legacy function exception handling."""
        # Setup mock to raise exception
        mock_ddgs.side_effect = Exception("API error")
        
        # Execute
        results = search_and_scrape_multiple_sources("test query")
        
        # Verify empty results on exception
        assert results == []


if __name__ == '__main__':
    pytest.main([__file__])