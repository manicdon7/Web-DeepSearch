"""
Caching layer for performance optimization of search operations.
Implements in-memory caching with TTL, statistics tracking, and cache warming.
"""
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from threading import Lock
import logging
from app.optimization_models import EnhancedSource

logger = logging.getLogger(__name__)


@dataclass
class CachedContent:
    """Data class representing cached content with metadata."""
    url: str
    content: EnhancedSource
    cached_at: datetime
    query_hash: str
    expiry_time: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Check if the cached content has expired."""
        return datetime.now() > self.expiry_time
    
    def access(self) -> None:
        """Update access statistics when content is retrieved."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStatistics:
    """Data class for tracking cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as a percentage."""
        return 100.0 - self.hit_rate
    
    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.total_requests += 1
    
    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total_requests += 1
    
    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1


class CacheManager:
    """
    In-memory cache manager with TTL support, statistics tracking, and cache warming.
    
    Features:
    - TTL-based expiration
    - LRU eviction when cache is full
    - Hit/miss statistics tracking
    - Cache warming for popular queries
    - Thread-safe operations
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of items to store in cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CachedContent] = {}
        self._lock = Lock()
        self.statistics = CacheStatistics()
        self._popular_queries: Set[str] = set()
        
        logger.info(f"CacheManager initialized with max_size={max_size}, default_ttl={default_ttl}")
    
    def _generate_cache_key(self, url: str, query: str) -> str:
        """
        Generate a cache key based on URL and query hash.
        
        Args:
            url: The source URL
            query: The search query
            
        Returns:
            A unique cache key string
        """
        # Normalize URL by removing trailing slashes and converting to lowercase
        normalized_url = url.rstrip('/').lower()
        
        # Create a hash of the query for consistent key generation
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        
        # Combine URL and query hash
        cache_key = f"{normalized_url}:{query_hash}"
        return cache_key
    
    def _generate_query_hash(self, query: str) -> str:
        """Generate a hash for the query for tracking purposes."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        current_time = datetime.now()
        expired_keys = [
            key for key, cached_content in self._cache.items()
            if cached_content.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self.statistics.record_eviction()
            logger.debug(f"Expired cache entry removed: {key}")
    
    def _evict_lru(self) -> None:
        """Evict the least recently used item when cache is full."""
        if not self._cache:
            return
        
        # Find the least recently accessed item
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self.statistics.record_eviction()
        logger.debug(f"LRU eviction: {lru_key}")
    
    def get_cached_content(self, url: str, query: str) -> Optional[EnhancedSource]:
        """
        Retrieve cached content for a URL and query combination.
        
        Args:
            url: The source URL
            query: The search query
            
        Returns:
            The cached EnhancedSource if found and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(url, query)
        
        with self._lock:
            # Clean up expired entries first
            self._cleanup_expired()
            
            cached_content = self._cache.get(cache_key)
            
            if cached_content is None:
                self.statistics.record_miss()
                logger.debug(f"Cache miss: {cache_key}")
                return None
            
            if cached_content.is_expired():
                del self._cache[cache_key]
                self.statistics.record_miss()
                self.statistics.record_eviction()
                logger.debug(f"Cache expired: {cache_key}")
                return None
            
            # Update access statistics
            cached_content.access()
            self.statistics.record_hit()
            logger.debug(f"Cache hit: {cache_key}")
            
            return cached_content.content
    
    def cache_content(self, content: EnhancedSource, query: str, ttl: Optional[int] = None) -> None:
        """
        Cache content for a URL and query combination.
        
        Args:
            content: The EnhancedSource to cache
            query: The search query
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._generate_cache_key(str(content.url), query)
        query_hash = self._generate_query_hash(query)
        
        cached_content = CachedContent(
            url=str(content.url),
            content=content,
            cached_at=datetime.now(),
            query_hash=query_hash,
            expiry_time=datetime.now() + timedelta(seconds=ttl)
        )
        
        with self._lock:
            # Clean up expired entries
            self._cleanup_expired()
            
            # If cache is full, evict LRU item
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                self._evict_lru()
            
            self._cache[cache_key] = cached_content
            logger.debug(f"Content cached: {cache_key} (TTL: {ttl}s)")
    
    def invalidate_url(self, url: str) -> int:
        """
        Invalidate all cached entries for a specific URL.
        
        Args:
            url: The URL to invalidate
            
        Returns:
            Number of entries invalidated
        """
        normalized_url = url.rstrip('/').lower()
        
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(f"{normalized_url}:")
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
                self.statistics.record_eviction()
            
            logger.info(f"Invalidated {len(keys_to_remove)} entries for URL: {url}")
            return len(keys_to_remove)
    
    def invalidate_query(self, query: str) -> int:
        """
        Invalidate all cached entries for a specific query.
        
        Args:
            query: The query to invalidate
            
        Returns:
            Number of entries invalidated
        """
        query_hash = self._generate_query_hash(query)
        
        with self._lock:
            keys_to_remove = [
                key for key, cached_content in self._cache.items()
                if cached_content.query_hash == query_hash
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
                self.statistics.record_eviction()
            
            logger.info(f"Invalidated {len(keys_to_remove)} entries for query: {query}")
            return len(keys_to_remove)
    
    def clear_cache(self) -> int:
        """
        Clear all cached entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
            return count
    
    def get_statistics(self) -> CacheStatistics:
        """Get current cache statistics."""
        return self.statistics
    
    def get_cache_info(self) -> Dict[str, any]:
        """
        Get detailed cache information.
        
        Returns:
            Dictionary containing cache size, statistics, and configuration
        """
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'default_ttl': self.default_ttl,
                'statistics': {
                    'hits': self.statistics.hits,
                    'misses': self.statistics.misses,
                    'evictions': self.statistics.evictions,
                    'total_requests': self.statistics.total_requests,
                    'hit_rate': self.statistics.hit_rate,
                    'miss_rate': self.statistics.miss_rate
                }
            }
    
    def add_popular_query(self, query: str) -> None:
        """
        Mark a query as popular for cache warming purposes.
        
        Args:
            query: The query to mark as popular
        """
        query_hash = self._generate_query_hash(query)
        self._popular_queries.add(query_hash)
        logger.debug(f"Query marked as popular: {query}")
    
    def get_popular_queries(self) -> List[str]:
        """Get list of popular query hashes."""
        return list(self._popular_queries)
    
    def warm_cache_for_query(self, query: str, sources: List[EnhancedSource], ttl: Optional[int] = None) -> int:
        """
        Pre-populate cache with content for a specific query (cache warming).
        
        Args:
            query: The query to warm cache for
            sources: List of EnhancedSource objects to cache
            ttl: Time-to-live for cached entries
            
        Returns:
            Number of entries added to cache
        """
        cached_count = 0
        
        for source in sources:
            # Only cache if not already present
            if self.get_cached_content(str(source.url), query) is None:
                self.cache_content(source, query, ttl)
                cached_count += 1
        
        logger.info(f"Cache warmed for query '{query}': {cached_count} entries added")
        return cached_count
    
    def cleanup_expired_entries(self) -> int:
        """
        Manually trigger cleanup of expired entries.
        
        Returns:
            Number of expired entries removed
        """
        with self._lock:
            initial_size = len(self._cache)
            self._cleanup_expired()
            removed_count = initial_size - len(self._cache)
            
            if removed_count > 0:
                logger.info(f"Manual cleanup removed {removed_count} expired entries")
            
            return removed_count