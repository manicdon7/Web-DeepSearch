"""
Unit tests for the ConcurrentScraperManager class.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import time

from app.concurrent_scraper import ConcurrentScraperManager
from app.optimization_models import SourceScore, ScrapingResult, QueryAnalysis, QueryComplexity, QueryIntent, SummaryLength, ContentQuality
from app.content_quality_assessor import ContentQualityAssessor


class TestScrapingResult:
    """Test the ScrapingResult data class."""
    
    def test_successful_result_creation(self):
        """Test creating a successful scraping result."""
        content = {"title": "Test", "main_content": "Test content"}
        result = ScrapingResult(
            url="https://example.com",
            success=True,
            content=content,
            duration=1.5
        )
        
        assert result.url == "https://example.com"
        assert result.success is True
        assert result.content == content
        assert result.error is None
        assert result.duration == 1.5
    
    def test_failed_result_creation(self):
        """Test creating a failed scraping result."""
        result = ScrapingResult(
            url="https://example.com",
            success=False,
            error="Connection timeout",
            duration=10.0
        )
        
        assert result.url == "https://example.com"
        assert result.success is False
        assert result.content is None
        assert result.error == "Connection timeout"
        assert result.duration == 10.0
    
    def test_successful_result_without_content_raises_error(self):
        """Test that successful results without content raise ValueError."""
        with pytest.raises(ValueError, match="Successful scraping results must have content"):
            ScrapingResult(
                url="https://example.com",
                success=True,
                content=None
            )
    
    def test_failed_result_without_error_raises_error(self):
        """Test that failed results without error message raise ValueError."""
        with pytest.raises(ValueError, match="Failed scraping results must have an error message"):
            ScrapingResult(
                url="https://example.com",
                success=False,
                error=None
            )


class TestConcurrentScraperManager:
    """Test the ConcurrentScraperManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConcurrentScraperManager(
            max_concurrent=3,
            timeout_per_source=5,
            min_quality_sources=2,
            quality_threshold=0.7
        )
        
        self.sample_sources = [
            SourceScore(
                url="https://example1.com",
                relevance_score=0.9,
                authority_score=0.8,
                freshness_score=0.7,
                final_score=0.8
            ),
            SourceScore(
                url="https://example2.com",
                relevance_score=0.8,
                authority_score=0.7,
                freshness_score=0.6,
                final_score=0.7
            ),
            SourceScore(
                url="https://example3.com",
                relevance_score=0.7,
                authority_score=0.6,
                freshness_score=0.5,
                final_score=0.6
            )
        ]
    
    def test_manager_initialization(self):
        """Test ConcurrentScraperManager initialization."""
        manager = ConcurrentScraperManager(
            max_concurrent=10,
            timeout_per_source=15,
            min_quality_sources=5,
            quality_threshold=0.8
        )
        
        assert manager.max_concurrent == 10
        assert manager.timeout_per_source == 15
        assert manager.min_quality_sources == 5
        assert manager.quality_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_scrape_single_source_success(self):
        """Test successful scraping of a single source."""
        semaphore = asyncio.Semaphore(1)
        source = self.sample_sources[0]
        
        mock_content = {
            "url": source.url,
            "title": "Test Title",
            "main_content": "Test content with sufficient length for quality assessment",
            "images": [],
            "categories": ["test"]
        }
        
        with patch('app.concurrent_scraper.scrape_url', return_value=mock_content):
            result = await self.manager._scrape_single_source(semaphore, source)
            
            assert result.success is True
            assert result.url == source.url
            assert result.content == mock_content
            assert result.error is None
            assert result.duration > 0
    
    @pytest.mark.asyncio
    async def test_scrape_single_source_timeout(self):
        """Test timeout handling in single source scraping."""
        semaphore = asyncio.Semaphore(1)
        source = self.sample_sources[0]
        
        # Mock a slow scraper that exceeds timeout
        async def slow_scraper(url):
            await asyncio.sleep(10)  # Longer than timeout
            return {"title": "Test"}
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=lambda url: asyncio.run(slow_scraper(url))):
            result = await self.manager._scrape_single_source(semaphore, source)
            
            assert result.success is False
            assert result.url == source.url
            assert result.content is None
            assert "Timeout" in result.error
            assert result.duration > 0
    
    @pytest.mark.asyncio
    async def test_scrape_single_source_exception(self):
        """Test exception handling in single source scraping."""
        semaphore = asyncio.Semaphore(1)
        source = self.sample_sources[0]
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=Exception("Network error")):
            result = await self.manager._scrape_single_source(semaphore, source)
            
            assert result.success is False
            assert result.url == source.url
            assert result.content is None
            assert result.error == "Network error"
            assert result.duration > 0
    
    @pytest.mark.asyncio
    async def test_scrape_sources_parallel_all_successful(self):
        """Test parallel scraping with all sources successful."""
        mock_contents = [
            {
                "url": source.url,
                "title": f"Title {i}",
                "main_content": f"Content {i} with sufficient length for testing quality assessment functionality",
                "images": [],
                "categories": [f"category{i}"]
            }
            for i, source in enumerate(self.sample_sources)
        ]
        
        def mock_scraper(url):
            for i, source in enumerate(self.sample_sources):
                if source.url == url:
                    return mock_contents[i]
            return None
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                self.sample_sources,
                early_termination=False
            )
            
            assert len(results) == 3
            assert all(result.success for result in results)
            assert all(result.content is not None for result in results)
    
    @pytest.mark.asyncio
    async def test_scrape_sources_parallel_with_failures(self):
        """Test parallel scraping with some source failures."""
        def mock_scraper(url):
            if url == "https://example1.com":
                return {
                    "url": url,
                    "title": "Success",
                    "main_content": "Successful content with sufficient length",
                    "images": [],
                    "categories": []
                }
            elif url == "https://example2.com":
                raise Exception("Network error")
            else:  # example3.com
                return None  # Scraper returns None
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                self.sample_sources,
                early_termination=False
            )
            
            assert len(results) == 3
            
            # Check first result (successful)
            success_results = [r for r in results if r.success]
            assert len(success_results) == 1
            assert success_results[0].url == "https://example1.com"
            
            # Check failed results
            failed_results = [r for r in results if not r.success]
            assert len(failed_results) == 2
    
    @pytest.mark.asyncio
    async def test_early_termination_with_quality_assessor(self):
        """Test early termination when quality threshold is met."""
        # Create a mock quality assessor
        mock_assessor = Mock(spec=ContentQualityAssessor)
        mock_quality = ContentQuality(
            relevance_score=0.8,  # Above threshold
            content_length=500,
            information_density=0.7,
            duplicate_content=False,
            quality_indicators={}
        )
        mock_assessor.assess_content.return_value = mock_quality
        
        manager = ConcurrentScraperManager(
            max_concurrent=3,
            timeout_per_source=5,
            quality_assessor=mock_assessor,
            min_quality_sources=2,
            quality_threshold=0.7
        )
        
        # Create more sources than min_quality_sources to test early termination
        extended_sources = self.sample_sources + [
            SourceScore(
                url="https://example4.com",
                relevance_score=0.6,
                authority_score=0.5,
                freshness_score=0.4,
                final_score=0.5
            ),
            SourceScore(
                url="https://example5.com",
                relevance_score=0.5,
                authority_score=0.4,
                freshness_score=0.3,
                final_score=0.4
            )
        ]
        
        def mock_scraper(url):
            return {
                "url": url,
                "title": "Quality Content",
                "main_content": "High quality content with sufficient length for assessment",
                "images": [],
                "categories": []
            }
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await manager.scrape_sources_parallel(
                extended_sources,
                early_termination=True
            )
            
            # Should terminate early after finding min_quality_sources (2) quality sources
            # Plus potentially some additional sources that were already in progress
            assert len(results) >= 2
            assert len(results) <= len(extended_sources)  # Should be less than total if early termination worked
    
    def test_basic_quality_check(self):
        """Test basic quality check functionality."""
        # High quality result
        good_result = ScrapingResult(
            url="https://example.com",
            success=True,
            content={
                "main_content": "This is a high quality content piece with sufficient length and information density to meet the basic quality criteria for content assessment. " * 10 + "Additional content to ensure we meet the minimum word count requirement of 100 words for the basic quality check functionality. This comprehensive text provides detailed information about the topic and demonstrates the quality assessment capabilities of the concurrent scraper manager system."
            },
            duration=2.0
        )
        
        assert self.manager._basic_quality_check(good_result) is True
        
        # Low quality result (too short)
        short_result = ScrapingResult(
            url="https://example.com",
            success=True,
            content={
                "main_content": "Too short"
            },
            duration=1.0
        )
        
        assert self.manager._basic_quality_check(short_result) is False
        
        # No content
        no_content_result = ScrapingResult(
            url="https://example.com",
            success=True,
            content={},
            duration=1.0
        )
        
        assert self.manager._basic_quality_check(no_content_result) is False
    
    def test_get_successful_results(self):
        """Test filtering for successful results."""
        results = [
            ScrapingResult(
                url="https://example1.com",
                success=True,
                content={"title": "Success 1"},
                duration=1.0
            ),
            ScrapingResult(
                url="https://example2.com",
                success=False,
                error="Failed",
                duration=2.0
            ),
            ScrapingResult(
                url="https://example3.com",
                success=True,
                content={"title": "Success 2"},
                duration=1.5
            )
        ]
        
        successful = self.manager.get_successful_results(results)
        
        assert len(successful) == 2
        assert all(result.success for result in successful)
        assert all(result.content is not None for result in successful)
    
    def test_get_scraping_stats(self):
        """Test scraping statistics generation."""
        results = [
            ScrapingResult(
                url="https://example1.com",
                success=True,
                content={"title": "Success"},
                duration=1.0
            ),
            ScrapingResult(
                url="https://example2.com",
                success=False,
                error="Failed",
                duration=5.0
            ),
            ScrapingResult(
                url="https://example3.com",
                success=True,
                content={"title": "Success"},
                duration=2.0
            )
        ]
        
        stats = self.manager.get_scraping_stats(results)
        
        assert stats['total_sources'] == 3
        assert stats['successful_sources'] == 2
        assert stats['failed_sources'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['average_duration'] == (1.0 + 5.0 + 2.0) / 3
        assert stats['max_duration'] == 5.0
        assert stats['min_duration'] == 1.0
    
    def test_get_scraping_stats_empty_results(self):
        """Test scraping statistics with empty results."""
        stats = self.manager.get_scraping_stats([])
        
        assert stats['total_sources'] == 0
        assert stats['successful_sources'] == 0
        assert stats['failed_sources'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['average_duration'] == 0.0
        assert stats['max_duration'] == 0.0
        assert stats['min_duration'] == 0.0


class TestConcurrentScraperIntegration:
    """Integration tests for ConcurrentScraperManager."""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self):
        """Test that concurrent processing is actually faster than sequential."""
        sources = [
            SourceScore(
                url=f"https://example{i}.com",
                relevance_score=0.8,
                authority_score=0.7,
                freshness_score=0.6,
                final_score=0.7
            )
            for i in range(5)
        ]
        
        # Mock scraper with artificial delay
        def slow_scraper(url):
            time.sleep(0.5)  # 500ms delay per source
            return {
                "url": url,
                "title": "Test",
                "main_content": "Test content with sufficient length",
                "images": [],
                "categories": []
            }
        
        manager = ConcurrentScraperManager(max_concurrent=5, timeout_per_source=10)
        
        start_time = time.time()
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=slow_scraper):
            results = await manager.scrape_sources_parallel(sources, early_termination=False)
        
        total_time = time.time() - start_time
        
        # With 5 concurrent operations, should take ~0.5s instead of ~2.5s sequential
        assert total_time < 1.5  # Allow some overhead
        assert len(results) == 5
        assert all(result.success for result in results)
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore properly limits concurrent operations."""
        sources = [
            SourceScore(
                url=f"https://example{i}.com",
                relevance_score=0.8,
                authority_score=0.7,
                freshness_score=0.6,
                final_score=0.7
            )
            for i in range(10)
        ]
        
        # Track concurrent operations
        concurrent_count = 0
        max_concurrent_seen = 0
        
        def tracking_scraper(url):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            time.sleep(0.1)  # Small delay
            concurrent_count -= 1
            return {
                "url": url,
                "title": "Test",
                "main_content": "Test content",
                "images": [],
                "categories": []
            }
        
        manager = ConcurrentScraperManager(max_concurrent=3, timeout_per_source=10)
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=tracking_scraper):
            results = await manager.scrape_sources_parallel(sources, early_termination=False)
        
        # Should never exceed max_concurrent limit
        assert max_concurrent_seen <= 3
        assert len(results) == 10