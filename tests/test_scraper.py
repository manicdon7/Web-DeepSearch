"""
Unit tests for enhanced scraper functionality with quality-focused extraction.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from datetime import datetime
from app.scraper import (
    extract_main_content,
    extract_images,
    extract_categories,
    calculate_word_count,
    calculate_information_density,
    detect_content_freshness,
    extract_structured_data,
    calculate_content_relevance_score,
    scrape_url,
    create_enhanced_source
)
from app.optimization_models import ContentQuality, EnhancedSource


class TestExtractMainContent:
    """Test cases for extract_main_content function."""
    
    def test_extract_from_article_tag(self):
        """Test extraction from semantic article tag."""
        html = """
        <html>
            <body>
                <nav>Navigation content</nav>
                <article>
                    <h1>Main Article</h1>
                    <p>This is the main content of the article.</p>
                    <p>Another paragraph with important information.</p>
                </article>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        content, quality_indicators = extract_main_content(soup)
        
        assert "Main Article" in content
        assert "main content of the article" in content
        assert "Navigation content" not in content
        assert "Footer content" not in content
        assert quality_indicators['semantic_container'] == 1.0
        assert quality_indicators['paragraph_count'] > 0
        assert quality_indicators['heading_structure'] > 0
    
    def test_extract_from_main_tag(self):
        """Test extraction from semantic main tag."""
        html = """
        <html>
            <body>
                <main>
                    <h2>Main Content</h2>
                    <p>Content in main tag.</p>
                </main>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        content, quality_indicators = extract_main_content(soup)
        
        assert "Main Content" in content
        assert "Content in main tag" in content
        assert quality_indicators['semantic_container'] == 1.0
    
    def test_fallback_to_body(self):
        """Test fallback to body when no semantic tags found."""
        html = """
        <html>
            <body>
                <div>Some content without semantic tags</div>
                <span>More content</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        content, quality_indicators = extract_main_content(soup)
        
        assert "Some content without semantic tags" in content
        assert "More content" in content
        assert quality_indicators['semantic_container'] == 0.3  # Lower quality for fallback
    
    def test_empty_content(self):
        """Test handling of empty or minimal content."""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        content, quality_indicators = extract_main_content(soup)
        
        assert content == ""
        assert quality_indicators['semantic_container'] == 0.3


class TestExtractImages:
    """Test cases for extract_images function."""
    
    def test_extract_images_with_absolute_urls(self):
        """Test extraction of images with absolute URLs."""
        html = """
        <html>
            <body>
                <img src="https://example.com/image1.jpg" alt="Image 1">
                <img src="https://example.com/image2.png" alt="Image 2">
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        images = extract_images(soup, "https://example.com")
        
        assert len(images) == 2
        assert images[0]['src'] == "https://example.com/image1.jpg"
        assert images[0]['alt'] == "Image 1"
        assert images[1]['src'] == "https://example.com/image2.png"
        assert images[1]['alt'] == "Image 2"
    
    def test_extract_images_with_relative_urls(self):
        """Test extraction of images with relative URLs."""
        html = """
        <html>
            <body>
                <img src="/images/photo.jpg" alt="Photo">
                <img src="assets/logo.png" alt="">
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        images = extract_images(soup, "https://example.com")
        
        assert len(images) == 2
        assert images[0]['src'] == "https://example.com/images/photo.jpg"
        assert images[0]['alt'] == "Photo"
        assert images[1]['src'] == "https://example.com/assets/logo.png"
        assert images[1]['alt'] == ""
    
    def test_filter_svg_and_gif(self):
        """Test filtering of SVG and GIF images."""
        html = """
        <html>
            <body>
                <img src="icon.svg" alt="Icon">
                <img src="animation.gif" alt="Animation">
                <img src="photo.jpg" alt="Photo">
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        images = extract_images(soup, "https://example.com")
        
        assert len(images) == 1
        assert images[0]['src'] == "https://example.com/photo.jpg"


class TestExtractCategories:
    """Test cases for extract_categories function."""
    
    def test_extract_from_meta_keywords(self):
        """Test extraction from meta keywords tag."""
        html = """
        <html>
            <head>
                <meta name="keywords" content="technology, programming, python, web development">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        categories = extract_categories(soup)
        
        assert "technology" in categories
        assert "programming" in categories
        assert "python" in categories
        assert "web development" in categories
    
    def test_extract_from_category_elements(self):
        """Test extraction from category/tag elements."""
        html = """
        <html>
            <body>
                <span class="category">Tech</span>
                <a class="tag">Python</a>
                <span class="post-tag">Tutorial</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        categories = extract_categories(soup)
        
        assert "Tech" in categories
        assert "Python" in categories
        assert "Tutorial" in categories
    
    def test_no_duplicates(self):
        """Test that duplicate categories are removed."""
        html = """
        <html>
            <head>
                <meta name="keywords" content="python, programming">
            </head>
            <body>
                <span class="category">python</span>
                <span class="tag">programming</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        categories = extract_categories(soup)
        
        # Should have unique categories only
        assert categories.count("python") == 1
        assert categories.count("programming") == 1


class TestCalculateWordCount:
    """Test cases for calculate_word_count function."""
    
    def test_normal_text(self):
        """Test word count for normal text."""
        content = "This is a test sentence with eight words total."
        assert calculate_word_count(content) == 9
    
    def test_empty_content(self):
        """Test word count for empty content."""
        assert calculate_word_count("") == 0
        assert calculate_word_count(None) == 0
    
    def test_whitespace_handling(self):
        """Test word count with extra whitespace."""
        content = "  This   has   extra   whitespace  "
        assert calculate_word_count(content) == 4


class TestCalculateInformationDensity:
    """Test cases for calculate_information_density function."""
    
    def test_high_density_content(self):
        """Test calculation for high-density content."""
        main_content = "This is the main article content with valuable information."
        html = f"<html><body><article>{main_content}</article></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        density = calculate_information_density(main_content, soup)
        assert 0.8 <= density <= 1.0  # Should be high density
    
    def test_low_density_content(self):
        """Test calculation for low-density content with lots of noise."""
        main_content = "Short main content."
        html = """
        <html>
            <body>
                <nav>Long navigation menu with many items and links</nav>
                <article>Short main content.</article>
                <aside>Sidebar with advertisements and related links</aside>
                <footer>Footer with copyright and many links</footer>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        density = calculate_information_density(main_content, soup)
        assert 0.0 <= density <= 0.5  # Should be low density
    
    def test_empty_content(self):
        """Test calculation for empty content."""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        density = calculate_information_density("", soup)
        assert density == 0.0


class TestDetectContentFreshness:
    """Test cases for detect_content_freshness function."""
    
    def test_article_published_time(self):
        """Test detection from article:published_time meta tag."""
        html = """
        <html>
            <head>
                <meta property="article:published_time" content="2024-01-15T10:30:00Z">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        last_updated, freshness_score = detect_content_freshness(soup)
        
        assert last_updated is not None
        assert isinstance(freshness_score, float)
        assert 0.0 <= freshness_score <= 1.0
    
    def test_time_datetime_tag(self):
        """Test detection from time tag with datetime attribute."""
        html = """
        <html>
            <body>
                <time datetime="2024-01-15">January 15, 2024</time>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        last_updated, freshness_score = detect_content_freshness(soup)
        
        assert last_updated is not None
        assert isinstance(freshness_score, float)
    
    def test_no_date_found(self):
        """Test handling when no date information is found."""
        html = "<html><body><p>Content without date</p></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        last_updated, freshness_score = detect_content_freshness(soup)
        
        assert last_updated is None
        assert freshness_score == 0.5  # Default neutral score
    
    def test_invalid_date_format(self):
        """Test handling of invalid date formats."""
        html = """
        <html>
            <head>
                <meta name="date" content="invalid-date-format">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        last_updated, freshness_score = detect_content_freshness(soup)
        
        assert last_updated is None
        assert freshness_score == 0.5


class TestExtractStructuredData:
    """Test cases for extract_structured_data function."""
    
    def test_json_ld_extraction(self):
        """Test extraction of JSON-LD structured data."""
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Test Article"
                }
                </script>
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        structured_data = extract_structured_data(soup)
        
        assert 'json_ld' in structured_data
        assert len(structured_data['json_ld']) == 1
        assert structured_data['json_ld'][0]['@type'] == 'Article'
    
    def test_open_graph_extraction(self):
        """Test extraction of Open Graph data."""
        html = """
        <html>
            <head>
                <meta property="og:title" content="Test Title">
                <meta property="og:description" content="Test Description">
                <meta property="og:type" content="article">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        structured_data = extract_structured_data(soup)
        
        assert 'open_graph' in structured_data
        assert structured_data['open_graph']['title'] == 'Test Title'
        assert structured_data['open_graph']['description'] == 'Test Description'
        assert structured_data['open_graph']['type'] == 'article'
    
    def test_twitter_card_extraction(self):
        """Test extraction of Twitter Card data."""
        html = """
        <html>
            <head>
                <meta name="twitter:card" content="summary">
                <meta name="twitter:title" content="Twitter Title">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        structured_data = extract_structured_data(soup)
        
        assert 'twitter_card' in structured_data
        assert structured_data['twitter_card']['card'] == 'summary'
        assert structured_data['twitter_card']['title'] == 'Twitter Title'
    
    def test_basic_meta_extraction(self):
        """Test extraction of basic meta description and author."""
        html = """
        <html>
            <head>
                <meta name="description" content="Page description">
                <meta name="author" content="John Doe">
            </head>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        structured_data = extract_structured_data(soup)
        
        assert structured_data['description'] == 'Page description'
        assert structured_data['author'] == 'John Doe'


class TestCalculateContentRelevanceScore:
    """Test cases for calculate_content_relevance_score function."""
    
    def test_high_relevance_content(self):
        """Test scoring for highly relevant content."""
        content = "Python programming tutorial for web development using Django framework"
        query = "python web development"
        title = "Python Web Development Guide"
        categories = ["programming", "python", "web"]
        
        score = calculate_content_relevance_score(content, query, title, categories)
        assert 0.5 <= score <= 1.0  # Should be high relevance
    
    def test_low_relevance_content(self):
        """Test scoring for low relevance content."""
        content = "Cooking recipes for Italian pasta dishes with tomato sauce"
        query = "python programming"
        title = "Italian Cooking Guide"
        
        score = calculate_content_relevance_score(content, query, title)
        assert 0.0 <= score <= 0.3  # Should be low relevance
    
    def test_exact_phrase_match(self):
        """Test bonus scoring for exact phrase matches."""
        content = "This article covers machine learning algorithms in detail"
        query = "machine learning"
        
        score = calculate_content_relevance_score(content, query)
        assert score >= 0.3  # Should get exact phrase bonus
    
    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        assert calculate_content_relevance_score("", "query") == 0.0
        assert calculate_content_relevance_score("content", "") == 0.0
        assert calculate_content_relevance_score("", "") == 0.0


class TestScrapeUrl:
    """Test cases for scrape_url function."""
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_successful_scraping(self, mock_scraper):
        """Test successful URL scraping with quality metrics."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head>
                <title>Test Article</title>
                <meta name="description" content="Test description">
                <meta property="article:published_time" content="2024-01-15T10:30:00Z">
            </head>
            <body>
                <article>
                    <h1>Test Article</h1>
                    <p>This is test content for the article.</p>
                    <p>Another paragraph with more information.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.return_value = mock_response
        mock_scraper.return_value = mock_scraper_instance
        
        result = scrape_url("https://example.com/article", "test query")
        
        assert result is not None
        assert result['url'] == "https://example.com/article"
        assert result['title'] == "Test Article"
        assert "test content" in result['main_content']
        assert 'content_quality' in result
        assert 'scraping_duration' in result
        assert 'word_count' in result
        assert result['word_count'] > 0
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_scraping_with_network_error(self, mock_scraper):
        """Test handling of network errors during scraping."""
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.side_effect = Exception("Network error")
        mock_scraper.return_value = mock_scraper_instance
        
        result = scrape_url("https://example.com/article")
        
        assert result is None
    
    @patch('app.scraper.cloudscraper.create_scraper')
    def test_scraping_without_query(self, mock_scraper):
        """Test scraping without providing a query."""
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head><title>Test</title></head>
            <body><article><p>Content</p></article></body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        
        mock_scraper_instance = Mock()
        mock_scraper_instance.get.return_value = mock_response
        mock_scraper.return_value = mock_scraper_instance
        
        result = scrape_url("https://example.com/article")
        
        assert result is not None
        assert result['relevance_score'] == 0.0  # No query provided


class TestCreateEnhancedSource:
    """Test cases for create_enhanced_source function."""
    
    def test_create_from_valid_data(self):
        """Test creation of EnhancedSource from valid scraped data."""
        scraped_data = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "main_content": "Test content",
            "images": [],
            "categories": ["test"],
            "content_quality": ContentQuality(
                relevance_score=0.8,
                content_length=100,
                information_density=0.7,
                duplicate_content=False,
                quality_indicators={}
            ),
            "scraping_duration": 1.5,
            "relevance_score": 0.8,
            "word_count": 100,
            "last_updated": datetime.now()
        }
        
        enhanced_source = create_enhanced_source(scraped_data)
        
        assert enhanced_source is not None
        assert isinstance(enhanced_source, EnhancedSource)
        assert str(enhanced_source.url) == "https://example.com/article"
        assert enhanced_source.title == "Test Article"
        assert enhanced_source.word_count == 100
    
    def test_create_from_none_data(self):
        """Test handling of None input."""
        result = create_enhanced_source(None)
        assert result is None
    
    def test_create_from_invalid_data(self):
        """Test handling of invalid data structure."""
        invalid_data = {
            "url": "invalid-url",  # Invalid URL format
            "title": "Test"
        }
        
        result = create_enhanced_source(invalid_data)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])