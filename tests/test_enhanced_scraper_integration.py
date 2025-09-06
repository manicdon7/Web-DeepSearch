"""
Integration tests for enhanced scraper functionality.
"""
import pytest
from unittest.mock import Mock, patch
from app.scraper import scrape_url, create_enhanced_source
from app.optimization_models import ContentQuality, EnhancedSource


class TestEnhancedScraperIntegration:
    """Integration tests for enhanced scraper with quality metrics."""
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_enhanced_scraper_with_quality_metrics(self, mock_scraper):
        """Test that enhanced scraper returns quality metrics and structured data."""
        # Mock response with rich HTML content
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head>
                <title>Python Web Development Tutorial</title>
                <meta name="description" content="Learn Python web development with Django">
                <meta name="author" content="John Doe">
                <meta name="keywords" content="python, web development, django, tutorial">
                <meta property="article:published_time" content="2024-01-15T10:30:00Z">
                <meta property="og:title" content="Python Web Development Tutorial">
                <meta property="og:description" content="Complete guide to Python web development">
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Python Web Development Tutorial"
                }
                </script>
            </head>
            <body>
                <nav>Navigation menu</nav>
                <article>
                    <h1>Python Web Development Tutorial</h1>
                    <p>This comprehensive tutorial covers Python web development using Django framework.</p>
                    <h2>Getting Started</h2>
                    <p>Django is a high-level Python web framework that encourages rapid development.</p>
                    <p>In this tutorial, you will learn how to build web applications with Python and Django.</p>
                    <ul>
                        <li>Setting up Django</li>
                        <li>Creating models</li>
                        <li>Building views</li>
                    </ul>
                    <img src="/images/django-logo.png" alt="Django Logo">
                </article>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.return_value = mock_response
        mock_scraper.return_value = mock_scraper_instance
        
        # Test scraping with query for relevance scoring
        query = "python web development django"
        result = scrape_url("https://example.com/python-tutorial", query)
        
        # Verify basic scraping functionality
        assert result is not None
        assert result['url'] == "https://example.com/python-tutorial"
        assert result['title'] == "Python Web Development Tutorial"
        assert "Django framework" in result['main_content']
        
        # Verify quality metrics are included
        assert 'content_quality' in result
        assert isinstance(result['content_quality'], ContentQuality)
        
        # Verify word count calculation
        assert 'word_count' in result
        assert result['word_count'] > 0
        
        # Verify relevance scoring with query
        assert 'relevance_score' in result
        assert result['relevance_score'] > 0.5  # Should be high relevance for matching query
        
        # Verify scraping duration tracking
        assert 'scraping_duration' in result
        assert result['scraping_duration'] > 0
        
        # Verify structured data extraction
        assert 'structured_data' in result
        structured_data = result['structured_data']
        assert 'json_ld' in structured_data
        assert 'open_graph' in structured_data
        assert 'description' in structured_data
        assert 'author' in structured_data
        
        # Verify content quality indicators
        quality = result['content_quality']
        assert quality.relevance_score > 0.5
        assert quality.content_length > 0
        assert quality.information_density > 0
        assert 'semantic_container' in quality.quality_indicators
        assert quality.quality_indicators['semantic_container'] == 1.0  # Found article tag
        
        # Verify freshness detection
        assert 'last_updated' in result
        assert result['last_updated'] is not None
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_enhanced_source_creation(self, mock_scraper):
        """Test creation of EnhancedSource from scraped data."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <article>
                    <h1>Test Article</h1>
                    <p>This is test content for enhanced source creation.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.return_value = mock_response
        mock_scraper.return_value = mock_scraper_instance
        
        # Scrape and create enhanced source
        scraped_data = scrape_url("https://example.com/test", "test query")
        enhanced_source = create_enhanced_source(scraped_data)
        
        # Verify enhanced source creation
        assert enhanced_source is not None
        assert isinstance(enhanced_source, EnhancedSource)
        assert str(enhanced_source.url) == "https://example.com/test"
        assert enhanced_source.title == "Test Article"
        assert enhanced_source.content_quality is not None
        assert enhanced_source.word_count is not None
        assert enhanced_source.word_count > 0
        assert enhanced_source.scraping_duration is not None
        assert enhanced_source.relevance_score is not None
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_backward_compatibility(self, mock_scraper):
        """Test that enhanced scraper maintains backward compatibility."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head><title>Simple Test</title></head>
            <body><p>Simple content</p></body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.return_value = mock_response
        mock_scraper.return_value = mock_scraper_instance
        
        # Test scraping without query (backward compatibility)
        result = scrape_url("https://example.com/simple")
        
        # Should still work and return basic structure
        assert result is not None
        assert result['url'] == "https://example.com/simple"
        assert result['title'] == "Simple Test"
        assert result['main_content'] == "Simple content"
        assert result['images'] == []
        assert result['categories'] == []
        
        # Enhanced features should still be present but with default values
        assert result['relevance_score'] == 0.0  # No query provided
        assert result['word_count'] > 0
        assert result['content_quality'] is not None
    
    def test_quality_metrics_calculation(self):
        """Test individual quality metric calculations."""
        from app.scraper import (
            calculate_word_count,
            calculate_information_density,
            calculate_content_relevance_score
        )
        from bs4 import BeautifulSoup
        
        # Test word count
        content = "This is a test sentence with seven words."
        assert calculate_word_count(content) == 8
        
        # Test information density
        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <article>Main content here</article>
                <footer>Footer</footer>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        main_content = "Main content here"
        density = calculate_information_density(main_content, soup)
        assert 0.0 < density < 1.0
        
        # Test relevance scoring
        content = "Python programming tutorial for web development"
        query = "python programming"
        score = calculate_content_relevance_score(content, query)
        assert score > 0.3  # Should have good relevance
        
        # Test with no relevance
        content = "Cooking recipes for pasta"
        query = "python programming"
        score = calculate_content_relevance_score(content, query)
        assert score < 0.2  # Should have low relevance


if __name__ == "__main__":
    pytest.main([__file__])