"""
Concurrent scraper manager for parallel processing of multiple sources.
"""
import asyncio
import time
from typing import List, Optional, Callable
import logging

from .optimization_models import SourceScore, ScrapingResult, ContentQuality
from .scraper import scrape_url
from .content_quality_assessor import ContentQualityAssessor

logger = logging.getLogger(__name__)


class ConcurrentScraperManager:
    """
    Manages parallel scraping operations with intelligent timeout and error handling.
    Implements early termination when sufficient quality content is gathered.
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        timeout_per_source: int = 10,
        quality_assessor: Optional[ContentQualityAssessor] = None,
        min_quality_sources: int = 3,
        quality_threshold: float = 0.7
    ):
        """
        Initialize the concurrent scraper manager.
        
        Args:
            max_concurrent: Maximum number of concurrent scraping operations
            timeout_per_source: Timeout in seconds for each source
            quality_assessor: ContentQualityAssessor instance for quality evaluation
            min_quality_sources: Minimum number of quality sources before early termination
            quality_threshold: Minimum quality score to consider a source as high quality
        """
        self.max_concurrent = max_concurrent
        self.timeout_per_source = timeout_per_source
        self.quality_assessor = quality_assessor
        self.min_quality_sources = min_quality_sources
        self.quality_threshold = quality_threshold
        
    async def scrape_sources_parallel(
        self,
        ranked_sources: List[SourceScore],
        query_analysis=None,
        early_termination: bool = True
    ) -> List[ScrapingResult]:
        """
        Scrape multiple sources in parallel with intelligent early termination.
        
        Args:
            ranked_sources: List of SourceScore objects ordered by relevance
            query_analysis: QueryAnalysis object for quality assessment
            early_termination: Whether to enable early termination based on quality
            
        Returns:
            List of ScrapingResult objects
        """
        logger.info(f"Starting parallel scraping of {len(ranked_sources)} sources")
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Track results and quality sources
        results = []
        quality_sources_count = 0
        
        # Create tasks for all sources
        tasks = []
        for source in ranked_sources:
            task = asyncio.create_task(
                self._scrape_single_source(semaphore, source, query_analysis)
            )
            tasks.append(task)
        
        # Process tasks as they complete
        try:
            for completed_task in asyncio.as_completed(tasks):
                try:
                    result = await completed_task
                    results.append(result)
                    
                    # Check if we should terminate early
                    if early_termination and self._should_terminate_early(
                        result, quality_sources_count, query_analysis
                    ):
                        quality_sources_count += 1
                        logger.info(
                            f"Found quality source ({quality_sources_count}/{self.min_quality_sources}): {result.url}"
                        )
                        
                        if quality_sources_count >= self.min_quality_sources:
                            logger.info("Early termination: sufficient quality content gathered")
                            # Cancel remaining tasks
                            for task in tasks:
                                if not task.done():
                                    task.cancel()
                            break
                    
                except asyncio.CancelledError:
                    logger.info("Task cancelled during early termination")
                    break
                except Exception as e:
                    logger.error(f"Error processing completed task: {e}")
                    
        except Exception as e:
            logger.error(f"Error in parallel scraping: {e}")
            # Cancel all remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        # Wait for any remaining tasks to complete or be cancelled
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Completed scraping with {len(results)} results")
        return results
    
    async def _scrape_single_source(
        self,
        semaphore: asyncio.Semaphore,
        source: SourceScore,
        query_analysis=None
    ) -> ScrapingResult:
        """
        Scrape a single source with timeout and error handling.
        
        Args:
            semaphore: Semaphore to limit concurrent operations
            source: SourceScore object containing URL and scoring info
            query_analysis: QueryAnalysis object for context
            
        Returns:
            ScrapingResult object
        """
        async with semaphore:
            start_time = time.time()
            
            try:
                # Run the synchronous scraper in a thread pool
                loop = asyncio.get_event_loop()
                content = await asyncio.wait_for(
                    loop.run_in_executor(None, scrape_url, source.url),
                    timeout=self.timeout_per_source
                )
                
                duration = time.time() - start_time
                
                if content is None:
                    return ScrapingResult(
                        url=source.url,
                        success=False,
                        error="Scraper returned None",
                        duration=duration
                    )
                
                logger.debug(f"Successfully scraped {source.url} in {duration:.2f}s")
                return ScrapingResult(
                    url=source.url,
                    success=True,
                    content=content,
                    duration=duration
                )
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                logger.warning(f"Timeout scraping {source.url} after {duration:.2f}s")
                return ScrapingResult(
                    url=source.url,
                    success=False,
                    error=f"Timeout after {self.timeout_per_source}s",
                    duration=duration
                )
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Error scraping {source.url}: {e}")
                return ScrapingResult(
                    url=source.url,
                    success=False,
                    error=str(e),
                    duration=duration
                )
    
    def _should_terminate_early(
        self,
        result: ScrapingResult,
        current_quality_count: int,
        query_analysis=None
    ) -> bool:
        """
        Determine if this result qualifies as high quality for early termination.
        
        Args:
            result: ScrapingResult to evaluate
            current_quality_count: Current count of quality sources found
            query_analysis: QueryAnalysis object for context
            
        Returns:
            True if this result is high quality and contributes to early termination
        """
        if not result.success or not result.content:
            return False
        
        # If no quality assessor is available, use basic heuristics
        if self.quality_assessor is None:
            return self._basic_quality_check(result)
        
        try:
            # Use the quality assessor to evaluate content
            quality = self.quality_assessor.assess_content(result.content, query_analysis)
            return quality.relevance_score >= self.quality_threshold
        except Exception as e:
            logger.error(f"Error assessing content quality for {result.url}: {e}")
            return self._basic_quality_check(result)
    
    def _basic_quality_check(self, result: ScrapingResult) -> bool:
        """
        Basic quality check when no quality assessor is available.
        
        Args:
            result: ScrapingResult to evaluate
            
        Returns:
            True if the content meets basic quality criteria
        """
        if not result.content or not result.content.get('main_content'):
            return False
        
        content = result.content['main_content']
        word_count = len(content.split())
        
        # Basic criteria: reasonable content length and successful scraping
        return (
            word_count >= 100 and  # Minimum content length
            len(content.strip()) > 200 and  # Minimum character count
            result.duration < self.timeout_per_source * 0.8  # Reasonable response time
        )
    
    def get_successful_results(self, results: List[ScrapingResult]) -> List[ScrapingResult]:
        """
        Filter results to only include successful scraping operations.
        
        Args:
            results: List of ScrapingResult objects
            
        Returns:
            List of successful ScrapingResult objects
        """
        return [result for result in results if result.success and result.content]
    
    def get_scraping_stats(self, results: List[ScrapingResult]) -> dict:
        """
        Generate statistics about the scraping operation.
        
        Args:
            results: List of ScrapingResult objects
            
        Returns:
            Dictionary containing scraping statistics
        """
        total_results = len(results)
        successful_results = len(self.get_successful_results(results))
        failed_results = total_results - successful_results
        
        if results:
            avg_duration = sum(r.duration for r in results) / len(results)
            max_duration = max(r.duration for r in results)
            min_duration = min(r.duration for r in results)
        else:
            avg_duration = max_duration = min_duration = 0.0
        
        return {
            'total_sources': total_results,
            'successful_sources': successful_results,
            'failed_sources': failed_results,
            'success_rate': successful_results / total_results if total_results > 0 else 0.0,
            'average_duration': avg_duration,
            'max_duration': max_duration,
            'min_duration': min_duration
        }