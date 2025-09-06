import asyncio
import logging
from typing import List, Dict, Optional
from ddgs import DDGS

from .query_analyzer import QueryAnalyzer
from .source_ranker import SourceRanker
from .concurrent_scraper import ConcurrentScraperManager
from .content_quality_assessor import ContentQualityAssessor
from .cache_manager import CacheManager
from .optimization_models import EnhancedSource, ScrapingResult

logger = logging.getLogger(__name__)

DOMAIN_BLOCKLIST = [
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "vimeo.com",
    "dailymotion.com",
    "pornhub.com",
    "xvideos.com",
    "xnxx.com",
    "ebay.com",
    "aliexpress.com",
    "fandom.com"
]


class OptimizedSearchClient:
    """
    Optimized search client with intelligent source selection and concurrent processing.
    """
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 timeout_per_source: int = 10,
                 max_sources: int = 15,
                 cache_ttl: int = 3600,
                 enable_early_termination: bool = True):
        """
        Initialize the optimized search client.
        
        Args:
            max_concurrent: Maximum concurrent scraping operations
            timeout_per_source: Timeout per source in seconds
            max_sources: Maximum number of sources to scrape
            cache_ttl: Cache time-to-live in seconds
            enable_early_termination: Whether to enable early termination
        """
        self.max_sources = max_sources
        self.enable_early_termination = enable_early_termination
        
        # Initialize optimization components
        self.query_analyzer = QueryAnalyzer()
        self.source_ranker = SourceRanker()
        self.content_quality_assessor = ContentQualityAssessor()
        self.cache_manager = CacheManager(default_ttl=cache_ttl)
        self.concurrent_scraper = ConcurrentScraperManager(
            max_concurrent=max_concurrent,
            timeout_per_source=timeout_per_source,
            quality_assessor=self.content_quality_assessor
        )
        
        logger.info("OptimizedSearchClient initialized with intelligent source selection")
    
    def search_and_scrape_multiple_sources(self, query: str) -> List[Dict]:
        """
        Performs optimized web search with intelligent source selection and concurrent scraping.
        
        Args:
            query: The user's search query
            
        Returns:
            List of dictionaries containing scraped data from high-quality sources
        """
        logger.info(f"Starting optimized search for query: '{query}'")
        
        try:
            # Step 1: Analyze the query
            query_analysis = self.query_analyzer.analyze_query(query)
            logger.info(f"Query analysis: complexity={query_analysis.complexity.value}, "
                       f"domain={query_analysis.domain}, intent={query_analysis.intent.value}")
            
            # Step 2: Perform web search
            search_results = self._perform_web_search(query)
            if not search_results:
                logger.warning("No search results found")
                return []
            
            # Step 3: Filter blocked domains
            filtered_results = self._filter_blocked_domains(search_results)
            logger.info(f"Filtered {len(search_results)} results to {len(filtered_results)} "
                       f"after removing blocked domains")
            
            # Step 4: Rank sources by relevance and quality
            ranked_sources = self.source_ranker.rank_sources(filtered_results, query_analysis)
            
            # Step 5: Limit to top sources
            top_sources = ranked_sources[:self.max_sources]
            logger.info(f"Selected top {len(top_sources)} sources for scraping")
            
            # Step 6: Check cache for existing content
            cached_sources, sources_to_scrape = self._check_cache(top_sources, query)
            logger.info(f"Found {len(cached_sources)} cached sources, "
                       f"need to scrape {len(sources_to_scrape)} sources")
            
            # Step 7: Scrape remaining sources concurrently
            scraped_results = []
            if sources_to_scrape:
                scraped_results = asyncio.run(
                    self.concurrent_scraper.scrape_sources_parallel(
                        sources_to_scrape, 
                        query_analysis, 
                        self.enable_early_termination
                    )
                )
            
            # Step 8: Process and cache successful results
            successful_sources = self._process_scraping_results(
                scraped_results, query, query_analysis
            )
            
            # Step 9: Combine cached and newly scraped sources
            all_sources = cached_sources + successful_sources
            
            # Step 10: Apply intelligent stopping criteria
            final_sources = self._apply_stopping_criteria(all_sources, query_analysis)
            
            logger.info(f"Completed optimized search: {len(final_sources)} high-quality sources")
            
            # Log performance statistics
            if scraped_results:
                stats = self.concurrent_scraper.get_scraping_stats(scraped_results)
                logger.info(f"Scraping stats: {stats['successful_sources']}/{stats['total_sources']} "
                           f"successful ({stats['success_rate']:.1%}), "
                           f"avg duration: {stats['average_duration']:.2f}s")
            
            return final_sources
            
        except Exception as e:
            logger.error(f"Error in optimized search: {e}")
            # Fallback to basic search if optimization fails
            return self._fallback_search(query)
    
    def _perform_web_search(self, query: str) -> List[Dict]:
        """Perform web search using DuckDuckGo."""
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=50))
                
                # Convert to standard format
                formatted_results = []
                for result in search_results:
                    formatted_results.append({
                        'url': result['href'],
                        'title': result.get('title', ''),
                        'snippet': result.get('body', '')
                    })
                
                return formatted_results
                
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return []
    
    def _filter_blocked_domains(self, search_results: List[Dict]) -> List[Dict]:
        """Filter out blocked domains from search results."""
        filtered_results = []
        
        for result in search_results:
            url = result['url']
            if not any(blocked_domain in url for blocked_domain in DOMAIN_BLOCKLIST):
                filtered_results.append(result)
            else:
                logger.debug(f"Filtered blocked domain: {url}")
        
        return filtered_results
    
    def _check_cache(self, ranked_sources, query: str) -> tuple[List[Dict], List]:
        """Check cache for existing content and return cached vs sources to scrape."""
        cached_sources = []
        sources_to_scrape = []
        
        for source in ranked_sources:
            cached_content = self.cache_manager.get_cached_content(source.url, query)
            
            if cached_content:
                # Convert EnhancedSource back to dict format
                cached_dict = {
                    'url': cached_content.url,
                    'title': cached_content.title,
                    'main_content': cached_content.main_content,
                    'images': cached_content.images,
                    'categories': cached_content.categories
                }
                cached_sources.append(cached_dict)
                logger.debug(f"Using cached content for: {source.url}")
            else:
                sources_to_scrape.append(source)
        
        return cached_sources, sources_to_scrape
    
    def _process_scraping_results(self, scraping_results: List[ScrapingResult], 
                                query: str, query_analysis) -> List[Dict]:
        """Process scraping results, assess quality, and cache successful results."""
        successful_sources = []
        
        for result in scraping_results:
            if not result.success or not result.content:
                logger.debug(f"Skipping failed scraping result: {result.url}")
                continue
            
            try:
                # Assess content quality
                quality = self.content_quality_assessor.assess_content(
                    result.content, query_analysis
                )
                
                # Only include high-quality content
                if (quality.relevance_score >= 0.3 and 
                    quality.content_length >= 50 and
                    quality.information_density >= 0.2):
                    
                    # Create EnhancedSource for caching
                    enhanced_source = EnhancedSource(
                        url=result.url,
                        title=result.content.get('title', ''),
                        main_content=result.content.get('main_content', ''),
                        images=result.content.get('images', []),
                        categories=result.content.get('categories', []),
                        content_quality=quality,
                        scraping_duration=result.duration,
                        relevance_score=quality.relevance_score,
                        word_count=quality.content_length
                    )
                    
                    # Cache the content
                    self.cache_manager.cache_content(enhanced_source, query)
                    
                    # Add to successful sources
                    successful_sources.append(result.content)
                    logger.debug(f"Added quality source: {result.url} "
                               f"(relevance: {quality.relevance_score:.2f})")
                else:
                    logger.debug(f"Filtered low-quality source: {result.url} "
                               f"(relevance: {quality.relevance_score:.2f})")
                    
            except Exception as e:
                logger.error(f"Error processing scraping result for {result.url}: {e}")
        
        return successful_sources
    
    def _apply_stopping_criteria(self, sources: List[Dict], query_analysis) -> List[Dict]:
        """Apply intelligent stopping criteria based on content quality."""
        if not sources:
            return sources
        
        # For simple queries, fewer sources might be sufficient
        if query_analysis.complexity.value == 'simple':
            max_sources = min(5, len(sources))
        elif query_analysis.complexity.value == 'moderate':
            max_sources = min(8, len(sources))
        else:  # complex
            max_sources = min(12, len(sources))
        
        # Return top sources up to the limit
        return sources[:max_sources]
    
    def _fallback_search(self, query: str) -> List[Dict]:
        """Fallback to basic search if optimization fails."""
        logger.warning("Using fallback search method")
        return search_and_scrape_multiple_sources(query)
    
    def get_cache_statistics(self) -> Dict:
        """Get cache performance statistics."""
        return self.cache_manager.get_cache_info()
    
    def clear_cache(self) -> int:
        """Clear the cache and return number of entries removed."""
        return self.cache_manager.clear_cache()


# Maintain backward compatibility with the original function
def search_and_scrape_multiple_sources(query: str) -> List[Dict]:
    """
    Legacy function for backward compatibility.
    Performs a basic web search and scrapes all available pages.
    
    Args:
        query: The user's search query.
    
    Returns:
        A list of dictionaries, where each dict contains the scraped data.
    """
    from . import scraper
    
    scraped_sources = []
    try:
        with DDGS() as ddgs:
            # Fetch as many results as possible
            search_results = list(ddgs.text(query, max_results=50))

            if not search_results:
                logger.warning("No search results found.")
                return []

            # Iterate through all results and scrape all valid sources
            for result in search_results:
                url = result['href']
                
                if any(blocked_domain in url for blocked_domain in DOMAIN_BLOCKLIST):
                    logger.debug(f"Skipping blocked domain: {url}")
                    continue

                logger.debug(f"Attempting to scrape: {url}")
                scraped_data = scraper.scrape_url(url)
                
                if scraped_data and scraped_data["main_content"].strip():
                    logger.debug(f"Successfully scraped: {url}")
                    scraped_sources.append(scraped_data)
            
            # Return all scraped sources without artificial limits
            return scraped_sources

    except Exception as e:
        logger.error(f"An error occurred during web search: {e}")
        return []
