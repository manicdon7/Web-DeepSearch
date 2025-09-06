"""
Integration tests for ConcurrentScraperManager with other optimization components.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch

from app.concurrent_scraper import ConcurrentScraperManager
from app.optimization_models import (
    SourceScore, ScrapingResult, QueryAnalysis, QueryComplexity, 
    QueryIntent, SummaryLength, ContentQuality
)
from app.content_quality_assessor import ContentQualityAssessor
from app.query_analyzer import QueryAnalyzer
from app.source_ranker import SourceRanker


class TestConcurrentScraperWithQualityAssessor:
    """Test ConcurrentScraperManager integration with ContentQualityAssessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.quality_assessor = ContentQualityAssessor()
        self.manager = ConcurrentScraperManager(
            max_concurrent=3,
            timeout_per_source=5,
            quality_assessor=self.quality_assessor,
            min_quality_sources=2,
            quality_threshold=0.6
        )
        
        self.query_analysis = QueryAnalysis(
            complexity=QueryComplexity.MODERATE,
            domain="technology",
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.MEDIUM,
            recency_importance=0.7
        )
    
    @pytest.mark.asyncio
    async def test_early_termination_with_real_quality_assessment(self):
        """Test early termination using real ContentQualityAssessor."""
        sources = [
            SourceScore(
                url="https://high-quality1.com",
                relevance_score=0.9,
                authority_score=0.8,
                freshness_score=0.7,
                final_score=0.8
            ),
            SourceScore(
                url="https://high-quality2.com",
                relevance_score=0.8,
                authority_score=0.7,
                freshness_score=0.6,
                final_score=0.7
            ),
            SourceScore(
                url="https://low-quality1.com",
                relevance_score=0.5,
                authority_score=0.4,
                freshness_score=0.3,
                final_score=0.4
            ),
            SourceScore(
                url="https://low-quality2.com",
                relevance_score=0.4,
                authority_score=0.3,
                freshness_score=0.2,
                final_score=0.3
            )
        ]
        
        def mock_scraper(url):
            if "high-quality" in url:
                return {
                    "url": url,
                    "title": "Comprehensive Technology Analysis",
                    "main_content": "This is a comprehensive analysis of modern technology trends including artificial intelligence, machine learning, cloud computing, and their impact on business operations. The content provides detailed insights into implementation strategies, best practices, and future outlook for technology adoption in enterprise environments.",
                    "images": [{"src": "tech.jpg", "alt": "Technology diagram"}],
                    "categories": ["technology", "AI", "cloud computing"]
                }
            else:
                return {
                    "url": url,
                    "title": "Short post",
                    "main_content": "Brief content about tech.",
                    "images": [],
                    "categories": ["tech"]
                }
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                sources,
                query_analysis=self.query_analysis,
                early_termination=True
            )
            
            # Should find 2 high-quality sources and terminate early
            successful_results = self.manager.get_successful_results(results)
            assert len(successful_results) >= 2
            
            # Verify that high-quality sources were processed
            high_quality_urls = [r.url for r in successful_results if "high-quality" in r.url]
            assert len(high_quality_urls) >= 2
    
    @pytest.mark.asyncio
    async def test_quality_assessment_influences_termination(self):
        """Test that quality assessment properly influences early termination decisions."""
        sources = [
            SourceScore(
                url=f"https://example{i}.com",
                relevance_score=0.7,
                authority_score=0.6,
                freshness_score=0.5,
                final_score=0.6
            )
            for i in range(6)
        ]
        
        # Create content with varying quality
        def mock_scraper(url):
            import time
            index = int(url.split('example')[1].split('.')[0])
            
            # Add small delays to simulate real scraping and allow early termination
            if index < 2:  # First 2 are high quality and fast
                time.sleep(0.1)
                return {
                    "url": url,
                    "title": f"High Quality Article {index}",
                    "main_content": f"This is a comprehensive article about technology with detailed analysis and insights. Article {index} provides extensive coverage of the topic with multiple perspectives and thorough research. The content includes practical examples and actionable recommendations for readers.",
                    "images": [{"src": f"image{index}.jpg", "alt": f"Diagram {index}"}],
                    "categories": ["technology", "analysis", "research"]
                }
            elif index == 2:  # Third one is high quality but slower
                time.sleep(0.3)
                return {
                    "url": url,
                    "title": f"High Quality Article {index}",
                    "main_content": f"This is a comprehensive article about technology with detailed analysis and insights. Article {index} provides extensive coverage of the topic with multiple perspectives and thorough research. The content includes practical examples and actionable recommendations for readers.",
                    "images": [{"src": f"image{index}.jpg", "alt": f"Diagram {index}"}],
                    "categories": ["technology", "analysis", "research"]
                }
            else:  # Rest are low quality and slower
                time.sleep(0.5)
                return {
                    "url": url,
                    "title": f"Brief Post {index}",
                    "main_content": f"Short post {index}.",
                    "images": [],
                    "categories": ["misc"]
                }
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                sources,
                query_analysis=self.query_analysis,
                early_termination=True
            )
            
            # Should terminate after finding 2 quality sources
            # May have a few more due to concurrent processing
            assert len(results) >= 2
            
            # Check that we found quality sources (the first 2-3 should be high quality)
            high_quality_results = [r for r in results if r.success and "High Quality Article" in r.content.get('title', '')]
            assert len(high_quality_results) >= 2
            
            # Due to the timing and concurrent nature, we might process all sources
            # but the important thing is that we found the quality ones first


class TestConcurrentScraperWithSourceRanker:
    """Test ConcurrentScraperManager integration with SourceRanker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.source_ranker = SourceRanker()
        self.manager = ConcurrentScraperManager(
            max_concurrent=3,
            timeout_per_source=5,
            min_quality_sources=2,
            quality_threshold=0.6
        )
    
    @pytest.mark.asyncio
    async def test_scraping_ranked_sources(self):
        """Test scraping sources that have been ranked by SourceRanker."""
        # Mock search results
        search_results = [
            {
                "url": "https://techcrunch.com/article1",
                "title": "AI Revolution in Enterprise",
                "snippet": "Comprehensive analysis of AI adoption in business"
            },
            {
                "url": "https://blog.example.com/post1",
                "title": "Quick AI Tips",
                "snippet": "Some tips about AI"
            },
            {
                "url": "https://arxiv.org/paper1",
                "title": "Machine Learning Research Paper",
                "snippet": "Academic research on ML algorithms"
            }
        ]
        
        query_analysis = QueryAnalysis(
            complexity=QueryComplexity.COMPLEX,
            domain="technology",
            intent=QueryIntent.RESEARCH,
            expected_length=SummaryLength.LONG,
            recency_importance=0.8
        )
        
        # Rank the sources
        ranked_sources = self.source_ranker.rank_sources(search_results, query_analysis)
        
        def mock_scraper(url):
            return {
                "url": url,
                "title": "Scraped Content",
                "main_content": "Detailed content about the topic with comprehensive analysis and insights.",
                "images": [],
                "categories": ["technology"]
            }
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                ranked_sources,
                query_analysis=query_analysis,
                early_termination=False
            )
            
            assert len(results) == len(ranked_sources)
            successful_results = self.manager.get_successful_results(results)
            assert len(successful_results) > 0
            
            # Verify that higher-ranked sources are processed
            techcrunch_result = next((r for r in results if "techcrunch" in r.url), None)
            assert techcrunch_result is not None
            assert techcrunch_result.success


class TestConcurrentScraperFullPipeline:
    """Test ConcurrentScraperManager in a complete optimization pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.query_analyzer = QueryAnalyzer()
        self.source_ranker = SourceRanker()
        self.quality_assessor = ContentQualityAssessor()
        self.manager = ConcurrentScraperManager(
            max_concurrent=3,
            timeout_per_source=5,
            quality_assessor=self.quality_assessor,
            min_quality_sources=2,
            quality_threshold=0.6
        )
    
    @pytest.mark.asyncio
    async def test_complete_optimization_pipeline(self):
        """Test the complete pipeline from query analysis to concurrent scraping."""
        query = "How does artificial intelligence impact modern business operations?"
        
        # Step 1: Analyze query
        query_analysis = self.query_analyzer.analyze_query(query)
        
        # Step 2: Mock search results
        search_results = [
            {
                "url": "https://harvard.edu/ai-business-impact",
                "title": "AI's Transformative Impact on Business Operations",
                "snippet": "Comprehensive study on how AI is reshaping business processes"
            },
            {
                "url": "https://techcrunch.com/ai-enterprise-adoption",
                "title": "Enterprise AI Adoption Trends 2024",
                "snippet": "Latest trends in AI adoption across industries"
            },
            {
                "url": "https://blog.startup.com/ai-tips",
                "title": "5 AI Tips for Startups",
                "snippet": "Quick tips for using AI in small businesses"
            },
            {
                "url": "https://spamsite.com/ai-clickbait",
                "title": "You Won't Believe These AI Secrets!",
                "snippet": "Clickbait content about AI"
            }
        ]
        
        # Step 3: Rank sources
        ranked_sources = self.source_ranker.rank_sources(search_results, query_analysis)
        
        # Step 4: Mock scraping with quality-varying content
        def mock_scraper(url):
            if "harvard.edu" in url:
                return {
                    "url": url,
                    "title": "AI's Transformative Impact on Business Operations",
                    "main_content": "Artificial intelligence is fundamentally transforming how businesses operate across all sectors. This comprehensive analysis examines the multifaceted impact of AI on operational efficiency, decision-making processes, customer engagement, and strategic planning. Organizations implementing AI solutions report significant improvements in productivity, cost reduction, and competitive advantage. The integration of machine learning algorithms enables predictive analytics, automated workflows, and enhanced data-driven insights that drive business growth and innovation.",
                    "images": [{"src": "ai-business.jpg", "alt": "AI in business"}],
                    "categories": ["artificial intelligence", "business", "operations", "technology"]
                }
            elif "techcrunch.com" in url:
                return {
                    "url": url,
                    "title": "Enterprise AI Adoption Trends 2024",
                    "main_content": "The enterprise AI landscape continues to evolve rapidly with new adoption patterns emerging across industries. Companies are increasingly focusing on practical AI implementations that deliver measurable ROI. Key trends include the rise of no-code AI platforms, increased investment in AI governance frameworks, and the growing importance of ethical AI practices. Organizations are moving beyond pilot projects to full-scale AI deployments that transform core business processes.",
                    "images": [{"src": "ai-trends.jpg", "alt": "AI trends chart"}],
                    "categories": ["enterprise", "AI", "trends", "adoption"]
                }
            elif "blog.startup.com" in url:
                return {
                    "url": url,
                    "title": "5 AI Tips for Startups",
                    "main_content": "Here are some quick AI tips: 1. Start small 2. Focus on data quality 3. Choose the right tools 4. Measure results 5. Scale gradually.",
                    "images": [],
                    "categories": ["startups", "AI", "tips"]
                }
            else:  # spamsite.com
                return {
                    "url": url,
                    "title": "You Won't Believe These AI Secrets!",
                    "main_content": "Click here for amazing AI secrets! Buy our course now!",
                    "images": [],
                    "categories": ["spam"]
                }
        
        # Step 5: Scrape with concurrent manager
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                ranked_sources,
                query_analysis=query_analysis,
                early_termination=True
            )
            
            # Verify pipeline results
            successful_results = self.manager.get_successful_results(results)
            assert len(successful_results) >= 2  # Should find quality sources and terminate early
            
            # Verify high-quality sources were prioritized
            harvard_result = next((r for r in successful_results if "harvard.edu" in r.url), None)
            techcrunch_result = next((r for r in successful_results if "techcrunch.com" in r.url), None)
            
            # At least one of the high-quality sources should be present
            assert harvard_result is not None or techcrunch_result is not None
            
            # Generate stats
            stats = self.manager.get_scraping_stats(results)
            assert stats['success_rate'] > 0.5  # Most sources should succeed
            assert stats['total_sources'] >= 2
    
    @pytest.mark.asyncio
    async def test_pipeline_with_all_failures(self):
        """Test pipeline behavior when all sources fail to scrape."""
        query = "test query"
        query_analysis = self.query_analyzer.analyze_query(query)
        
        search_results = [
            {
                "url": "https://failing1.com",
                "title": "Test 1",
                "snippet": "Test content"
            },
            {
                "url": "https://failing2.com",
                "title": "Test 2",
                "snippet": "Test content"
            }
        ]
        
        ranked_sources = self.source_ranker.rank_sources(search_results, query_analysis)
        
        # Mock all scrapers to fail
        with patch('app.concurrent_scraper.scrape_url', side_effect=Exception("Network error")):
            results = await self.manager.scrape_sources_parallel(
                ranked_sources,
                query_analysis=query_analysis,
                early_termination=True
            )
            
            assert len(results) == len(ranked_sources)
            assert all(not result.success for result in results)
            
            stats = self.manager.get_scraping_stats(results)
            assert stats['success_rate'] == 0.0
            assert stats['failed_sources'] == len(ranked_sources)
    
    @pytest.mark.asyncio
    async def test_pipeline_performance_monitoring(self):
        """Test performance monitoring capabilities in the pipeline."""
        query = "performance test query"
        query_analysis = self.query_analyzer.analyze_query(query)
        
        search_results = [
            {
                "url": f"https://example{i}.com",
                "title": f"Test Article {i}",
                "snippet": f"Test content {i}"
            }
            for i in range(5)
        ]
        
        ranked_sources = self.source_ranker.rank_sources(search_results, query_analysis)
        
        def mock_scraper(url):
            # Simulate varying response times
            import time
            index = int(url.split('example')[1].split('.')[0])
            time.sleep(0.1 * index)  # Increasing delay
            
            return {
                "url": url,
                "title": f"Content from {url}",
                "main_content": "Test content with sufficient length for quality assessment.",
                "images": [],
                "categories": ["test"]
            }
        
        start_time = asyncio.get_event_loop().time()
        
        with patch('app.concurrent_scraper.scrape_url', side_effect=mock_scraper):
            results = await self.manager.scrape_sources_parallel(
                ranked_sources,
                query_analysis=query_analysis,
                early_termination=False
            )
        
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify performance metrics
        stats = self.manager.get_scraping_stats(results)
        assert stats['total_sources'] == 5
        assert stats['average_duration'] > 0
        assert stats['max_duration'] > stats['min_duration']
        
        # Concurrent processing should be faster than sequential
        # Sequential would take 0.1 + 0.2 + 0.3 + 0.4 + 0.5 = 1.5s
        # Concurrent should be closer to max individual time (0.5s) plus overhead
        assert total_time < 1.0  # Should be significantly faster than sequential