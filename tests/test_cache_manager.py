"""
Unit tests for the CacheManager class.
Tests caching functionality, TTL behavior, statistics tracking, and cache warming.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.cache_manager import CacheManager, CachedContent, CacheStatistics
from app.optimization_models import EnhancedSource, ContentQuality


@pytest.fixture
def cache_manager():
    """Create a CacheManager instance for testing."""
    return CacheManager(max_size=5, default_ttl=3600)


@pytest.fixture
def sample_enhanced_source():
    """Create a sample EnhancedSource for testing."""
    return EnhancedSource(
        url="https://example.com/article",
        title="Test Article",
        main_content="This is test content for the article.",
        images=[],
        categories=["tech"],
        word_count=8
    )


@pytest.fixture
def sample_enhanced_source_2():
    """Create another sample EnhancedSource for testing."""
    return EnhancedSource(
        url="https://example.com/article2",
        title="Test Article 2",
        main_content="This is different test content.",
        images=[],
        categories=["science"],
        word_count=6
    )


class TestCacheManager:
    """Test cases for CacheManager functionality."""
    
    def test_initialization(self):
        """Test CacheManager initialization with custom parameters."""
        cache = CacheManager(max_size=100, default_ttl=7200)
        assert cache.max_size == 100
        assert cache.default_ttl == 7200
        assert len(cache._cache) == 0
        assert cache.statistics.hits == 0
        assert cache.statistics.misses == 0
    
    def test_cache_key_generation(self, cache_manager):
        """Test cache key generation from URL and query."""
        key1 = cache_manager._generate_cache_key("https://example.com", "test query")
        key2 = cache_manager._generate_cache_key("https://example.com/", "test query")
        key3 = cache_manager._generate_cache_key("https://example.com", "Test Query")
        key4 = cache_manager._generate_cache_key("https://example.com", "different query")
        
        # Same URL (with/without trailing slash) and same query should generate same key
        assert key1 == key2
        assert key1 == key3  # Case insensitive
        assert key1 != key4  # Different query should generate different key
    
    def test_query_hash_generation(self, cache_manager):
        """Test query hash generation."""
        hash1 = cache_manager._generate_query_hash("test query")
        hash2 = cache_manager._generate_query_hash("Test Query")
        hash3 = cache_manager._generate_query_hash("  test query  ")
        hash4 = cache_manager._generate_query_hash("different query")
        
        # Same query with different cases/whitespace should generate same hash
        assert hash1 == hash2
        assert hash1 == hash3
        assert hash1 != hash4
    
    def test_cache_and_retrieve_content(self, cache_manager, sample_enhanced_source):
        """Test basic caching and retrieval functionality."""
        query = "test query"
        
        # Initially should be cache miss
        result = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        assert result is None
        assert cache_manager.statistics.misses == 1
        assert cache_manager.statistics.hits == 0
        
        # Cache the content
        cache_manager.cache_content(sample_enhanced_source, query)
        
        # Should now be cache hit
        result = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        assert result is not None
        assert result.url == sample_enhanced_source.url
        assert result.title == sample_enhanced_source.title
        assert cache_manager.statistics.hits == 1
        assert cache_manager.statistics.misses == 1
    
    def test_cache_with_custom_ttl(self, cache_manager, sample_enhanced_source):
        """Test caching with custom TTL."""
        query = "test query"
        custom_ttl = 1800  # 30 minutes
        
        cache_manager.cache_content(sample_enhanced_source, query, ttl=custom_ttl)
        
        # Verify content is cached
        result = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        assert result is not None
        
        # Check that the cached entry has correct expiry time
        cache_key = cache_manager._generate_cache_key(str(sample_enhanced_source.url), query)
        cached_content = cache_manager._cache[cache_key]
        expected_expiry = cached_content.cached_at + timedelta(seconds=custom_ttl)
        assert abs((cached_content.expiry_time - expected_expiry).total_seconds()) < 1
    
    def test_cache_expiration(self, cache_manager, sample_enhanced_source):
        """Test that expired content is not returned."""
        query = "test query"
        
        # Cache with very short TTL
        cache_manager.cache_content(sample_enhanced_source, query, ttl=1)
        
        # Should be available immediately
        result = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        assert result is not None
        
        # Mock time to simulate expiration
        with patch('app.cache_manager.datetime') as mock_datetime:
            # Set current time to 2 seconds in the future
            future_time = datetime.now() + timedelta(seconds=2)
            mock_datetime.now.return_value = future_time
            
            # Should now be expired and return None
            result = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
            assert result is None
            assert cache_manager.statistics.misses == 1  # Only the expired miss (no initial miss since we cached first)
    
    def test_cache_size_limit_and_lru_eviction(self, cache_manager):
        """Test that cache respects size limit and evicts LRU items."""
        # Fill cache to capacity (max_size = 5)
        sources = []
        for i in range(5):
            source = EnhancedSource(
                url=f"https://example.com/article{i}",
                title=f"Article {i}",
                main_content=f"Content {i}",
                images=[],
                categories=["test"]
            )
            sources.append(source)
            cache_manager.cache_content(source, f"query{i}")
        
        # All should be cached
        assert len(cache_manager._cache) == 5
        
        # Access first few items to update their access time
        for i in range(3):
            cache_manager.get_cached_content(f"https://example.com/article{i}", f"query{i}")
        
        # Add one more item, should evict LRU (article3 or article4)
        new_source = EnhancedSource(
            url="https://example.com/new-article",
            title="New Article",
            main_content="New content",
            images=[],
            categories=["test"]
        )
        cache_manager.cache_content(new_source, "new query")
        
        # Cache should still be at max size
        assert len(cache_manager._cache) == 5
        assert cache_manager.statistics.evictions == 1
        
        # The new item should be cached
        result = cache_manager.get_cached_content("https://example.com/new-article", "new query")
        assert result is not None
    
    def test_invalidate_url(self, cache_manager, sample_enhanced_source, sample_enhanced_source_2):
        """Test invalidating all cache entries for a specific URL."""
        # Cache same URL with different queries
        cache_manager.cache_content(sample_enhanced_source, "query1")
        cache_manager.cache_content(sample_enhanced_source, "query2")
        cache_manager.cache_content(sample_enhanced_source_2, "query1")
        
        assert len(cache_manager._cache) == 3
        
        # Invalidate entries for first URL
        invalidated = cache_manager.invalidate_url(str(sample_enhanced_source.url))
        assert invalidated == 2
        assert len(cache_manager._cache) == 1
        
        # Only the second URL should remain
        result = cache_manager.get_cached_content(str(sample_enhanced_source_2.url), "query1")
        assert result is not None
    
    def test_invalidate_query(self, cache_manager, sample_enhanced_source, sample_enhanced_source_2):
        """Test invalidating all cache entries for a specific query."""
        # Cache different URLs with same and different queries
        cache_manager.cache_content(sample_enhanced_source, "common query")
        cache_manager.cache_content(sample_enhanced_source_2, "common query")
        cache_manager.cache_content(sample_enhanced_source, "different query")
        
        assert len(cache_manager._cache) == 3
        
        # Invalidate entries for common query
        invalidated = cache_manager.invalidate_query("common query")
        assert invalidated == 2
        assert len(cache_manager._cache) == 1
        
        # Only the different query should remain
        result = cache_manager.get_cached_content(str(sample_enhanced_source.url), "different query")
        assert result is not None
    
    def test_clear_cache(self, cache_manager, sample_enhanced_source):
        """Test clearing all cache entries."""
        # Add some entries
        cache_manager.cache_content(sample_enhanced_source, "query1")
        cache_manager.cache_content(sample_enhanced_source, "query2")
        
        assert len(cache_manager._cache) == 2
        
        # Clear cache
        cleared = cache_manager.clear_cache()
        assert cleared == 2
        assert len(cache_manager._cache) == 0
    
    def test_statistics_tracking(self, cache_manager, sample_enhanced_source):
        """Test that cache statistics are tracked correctly."""
        query = "test query"
        
        # Initial state
        stats = cache_manager.get_statistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_requests == 0
        assert stats.hit_rate == 0.0
        
        # Cache miss
        cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        stats = cache_manager.get_statistics()
        assert stats.misses == 1
        assert stats.total_requests == 1
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 100.0
        
        # Cache content and hit
        cache_manager.cache_content(sample_enhanced_source, query)
        cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        
        stats = cache_manager.get_statistics()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.total_requests == 2
        assert stats.hit_rate == 50.0
        assert stats.miss_rate == 50.0
    
    def test_cache_info(self, cache_manager, sample_enhanced_source):
        """Test getting detailed cache information."""
        cache_manager.cache_content(sample_enhanced_source, "test query")
        
        info = cache_manager.get_cache_info()
        
        assert info['size'] == 1
        assert info['max_size'] == 5
        assert info['default_ttl'] == 3600
        assert 'statistics' in info
        assert info['statistics']['hits'] == 0
        assert info['statistics']['misses'] == 0
    
    def test_popular_queries_management(self, cache_manager):
        """Test adding and retrieving popular queries."""
        # Initially no popular queries
        assert len(cache_manager.get_popular_queries()) == 0
        
        # Add popular queries
        cache_manager.add_popular_query("popular query 1")
        cache_manager.add_popular_query("popular query 2")
        cache_manager.add_popular_query("popular query 1")  # Duplicate
        
        popular_queries = cache_manager.get_popular_queries()
        assert len(popular_queries) == 2  # Should deduplicate
    
    def test_cache_warming(self, cache_manager, sample_enhanced_source, sample_enhanced_source_2):
        """Test cache warming functionality."""
        query = "warm query"
        sources = [sample_enhanced_source, sample_enhanced_source_2]
        
        # Warm cache
        cached_count = cache_manager.warm_cache_for_query(query, sources)
        assert cached_count == 2
        
        # Verify content is cached
        result1 = cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        result2 = cache_manager.get_cached_content(str(sample_enhanced_source_2.url), query)
        
        assert result1 is not None
        assert result2 is not None
        assert cache_manager.statistics.hits == 2
        
        # Warming again should not add duplicates
        cached_count = cache_manager.warm_cache_for_query(query, sources)
        assert cached_count == 0  # No new entries added
    
    def test_manual_cleanup_expired_entries(self, cache_manager, sample_enhanced_source):
        """Test manual cleanup of expired entries."""
        # Cache with short TTL
        cache_manager.cache_content(sample_enhanced_source, "test query", ttl=1)
        assert len(cache_manager._cache) == 1
        
        # Mock time to simulate expiration
        with patch('app.cache_manager.datetime') as mock_datetime:
            future_time = datetime.now() + timedelta(seconds=2)
            mock_datetime.now.return_value = future_time
            
            # Manual cleanup should remove expired entry
            removed = cache_manager.cleanup_expired_entries()
            assert removed == 1
            assert len(cache_manager._cache) == 0
    
    def test_access_count_tracking(self, cache_manager, sample_enhanced_source):
        """Test that access count is tracked for cached content."""
        query = "test query"
        cache_manager.cache_content(sample_enhanced_source, query)
        
        cache_key = cache_manager._generate_cache_key(str(sample_enhanced_source.url), query)
        cached_content = cache_manager._cache[cache_key]
        
        # Initial access count should be 0
        assert cached_content.access_count == 0
        
        # Access content multiple times
        for i in range(3):
            cache_manager.get_cached_content(str(sample_enhanced_source.url), query)
        
        # Access count should be updated
        assert cached_content.access_count == 3


class TestCachedContent:
    """Test cases for CachedContent data class."""
    
    def test_cached_content_creation(self, sample_enhanced_source):
        """Test CachedContent creation and properties."""
        cached_at = datetime.now()
        expiry_time = cached_at + timedelta(hours=1)
        
        cached_content = CachedContent(
            url=str(sample_enhanced_source.url),
            content=sample_enhanced_source,
            cached_at=cached_at,
            query_hash="test_hash",
            expiry_time=expiry_time
        )
        
        assert cached_content.url == str(sample_enhanced_source.url)
        assert cached_content.content == sample_enhanced_source
        assert cached_content.access_count == 0
        assert not cached_content.is_expired()
    
    def test_expiration_check(self, sample_enhanced_source):
        """Test expiration checking."""
        cached_at = datetime.now()
        expiry_time = cached_at - timedelta(minutes=1)  # Already expired
        
        cached_content = CachedContent(
            url=str(sample_enhanced_source.url),
            content=sample_enhanced_source,
            cached_at=cached_at,
            query_hash="test_hash",
            expiry_time=expiry_time
        )
        
        assert cached_content.is_expired()
    
    def test_access_tracking(self, sample_enhanced_source):
        """Test access count and timestamp tracking."""
        cached_content = CachedContent(
            url=str(sample_enhanced_source.url),
            content=sample_enhanced_source,
            cached_at=datetime.now(),
            query_hash="test_hash",
            expiry_time=datetime.now() + timedelta(hours=1)
        )
        
        initial_access_time = cached_content.last_accessed
        initial_count = cached_content.access_count
        
        # Simulate access
        cached_content.access()
        
        assert cached_content.access_count == initial_count + 1
        assert cached_content.last_accessed > initial_access_time


class TestCacheStatistics:
    """Test cases for CacheStatistics data class."""
    
    def test_statistics_initialization(self):
        """Test CacheStatistics initialization."""
        stats = CacheStatistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.total_requests == 0
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 100.0  # When no requests, miss_rate is 100 - hit_rate = 100
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStatistics()
        
        # Record some hits and misses
        stats.record_hit()
        stats.record_hit()
        stats.record_miss()
        
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.total_requests == 3
        assert abs(stats.hit_rate - 66.67) < 0.01  # 2/3 * 100
        assert abs(stats.miss_rate - 33.33) < 0.01  # 1/3 * 100
    
    def test_eviction_tracking(self):
        """Test eviction tracking."""
        stats = CacheStatistics()
        
        stats.record_eviction()
        stats.record_eviction()
        
        assert stats.evictions == 2