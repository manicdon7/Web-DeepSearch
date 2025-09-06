"""
Simplified integration tests for the main API performance monitoring features.
Tests core functionality without external dependencies.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

# Test the performance monitor and request timer directly
from app.performance_monitor import PerformanceMonitor, RequestTimer
from app.model import PerformanceMetrics, SystemMetrics


class TestPerformanceMonitor:
    """Test suite for the PerformanceMonitor class"""
    
    def setup_method(self):
        """Setup a fresh performance monitor for each test"""
        self.monitor = PerformanceMonitor()
    
    def test_request_tracking(self):
        """Test request start/end tracking"""
        start_time = self.monitor.record_request_start()
        assert self.monitor.request_count == 1
        
        time.sleep(0.01)  # Small delay
        self.monitor.record_request_end(start_time, success=True)
        
        assert len(self.monitor.response_times) == 1
        assert self.monitor.response_times[0] > 0
        assert self.monitor.error_count == 0
    
    def test_error_tracking(self):
        """Test error tracking"""
        start_time = self.monitor.record_request_start()
        self.monitor.record_request_end(start_time, success=False)
        
        assert self.monitor.error_count == 1
    
    def test_cache_tracking(self):
        """Test cache hit/miss tracking"""
        self.monitor.record_cache_hit()
        self.monitor.record_cache_hit()
        self.monitor.record_cache_miss()
        
        assert self.monitor.cache_hits == 2
        assert self.monitor.cache_misses == 1
    
    def test_system_metrics_calculation(self):
        """Test system metrics calculation"""
        # Record some test data
        start_time = self.monitor.record_request_start()
        self.monitor.record_request_end(start_time, success=True)
        
        start_time = self.monitor.record_request_start()
        self.monitor.record_request_end(start_time, success=False)
        
        self.monitor.record_cache_hit()
        self.monitor.record_cache_miss()
        
        metrics = self.monitor.get_system_metrics()
        
        assert metrics.requests_total == 2
        assert metrics.error_rate_percent == 50.0  # 1 error out of 2 requests
        assert metrics.cache_hit_rate_percent == 50.0  # 1 hit out of 2 cache requests
        assert metrics.average_response_time_ms >= 0
    
    def test_uptime_tracking(self):
        """Test uptime calculation"""
        uptime = self.monitor.get_uptime()
        assert uptime >= 0
        
        time.sleep(0.01)
        new_uptime = self.monitor.get_uptime()
        assert new_uptime > uptime


class TestRequestTimer:
    """Test suite for the RequestTimer utility"""
    
    def test_request_timer_basic_functionality(self):
        """Test basic request timer functionality"""
        timer = RequestTimer().start_request()
        
        # Test phase timing
        with timer.time_phase("test_phase"):
            time.sleep(0.01)  # 10ms
        
        # Verify timing (allow some variance for system overhead)
        assert timer.get_phase_duration("test_phase") > 5  # At least 5ms
        assert timer.get_total_duration() > 5
    
    def test_request_timer_multiple_phases(self):
        """Test timing multiple phases"""
        timer = RequestTimer().start_request()
        
        with timer.time_phase("phase1"):
            time.sleep(0.01)
        
        with timer.time_phase("phase2"):
            time.sleep(0.01)
        
        # Verify both phases were timed
        assert timer.get_phase_duration("phase1") > 0
        assert timer.get_phase_duration("phase2") > 0
        assert timer.get_total_duration() > timer.get_phase_duration("phase1")
        assert timer.get_total_duration() > timer.get_phase_duration("phase2")
    
    def test_create_performance_metrics(self):
        """Test creating performance metrics from timer"""
        timer = RequestTimer().start_request()
        
        with timer.time_phase("search"):
            time.sleep(0.01)
        
        with timer.time_phase("synthesis"):
            time.sleep(0.01)
        
        metrics = timer.create_performance_metrics(
            sources_found=5,
            sources_scraped=3,
            sources_failed=2,
            cache_hits=1,
            cache_misses=4
        )
        
        # Verify metrics structure
        assert metrics.sources_found == 5
        assert metrics.sources_scraped == 3
        assert metrics.sources_failed == 2
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 4
        assert metrics.search_duration_ms > 0
        assert metrics.synthesis_duration_ms > 0
        assert metrics.total_duration_ms > 0
        assert isinstance(metrics.timestamp, datetime)
    
    def test_timer_without_phases(self):
        """Test timer behavior when no phases are defined"""
        timer = RequestTimer().start_request()
        time.sleep(0.01)
        
        # Should still track total duration
        assert timer.get_total_duration() > 0
        
        # Non-existent phase should return 0
        assert timer.get_phase_duration("nonexistent") == 0.0


class TestConfigurationIntegration:
    """Test configuration integration"""
    
    def test_optimization_settings_defaults(self):
        """Test that optimization settings have reasonable defaults"""
        from app.config import OptimizationSettings
        
        settings = OptimizationSettings()
        
        # Verify default values are reasonable
        assert settings.max_concurrent_scrapers > 0
        assert settings.scraper_timeout_seconds > 0
        assert settings.cache_ttl_seconds > 0
        assert isinstance(settings.enable_caching, bool)
        assert isinstance(settings.enable_performance_monitoring, bool)
        assert 0 <= settings.min_content_quality_score <= 1
        assert 0 <= settings.min_relevance_score <= 1
    
    def test_settings_environment_override(self):
        """Test that environment variables can override settings"""
        import os
        from app.config import OptimizationSettings
        
        # Set environment variable
        os.environ["OPTIMIZATION_MAX_CONCURRENT_SCRAPERS"] = "10"
        
        try:
            settings = OptimizationSettings()
            assert settings.max_concurrent_scrapers == 10
        finally:
            # Clean up
            if "OPTIMIZATION_MAX_CONCURRENT_SCRAPERS" in os.environ:
                del os.environ["OPTIMIZATION_MAX_CONCURRENT_SCRAPERS"]


class TestModelValidation:
    """Test model validation and structure"""
    
    def test_performance_metrics_model(self):
        """Test PerformanceMetrics model validation"""
        metrics = PerformanceMetrics(
            total_duration_ms=100.5,
            search_duration_ms=30.0,
            scraping_duration_ms=50.0,
            synthesis_duration_ms=20.5,
            sources_found=10,
            sources_scraped=8,
            sources_failed=2,
            cache_hits=3,
            cache_misses=5,
            timestamp=datetime.now()
        )
        
        assert metrics.total_duration_ms == 100.5
        assert metrics.sources_found == 10
        assert isinstance(metrics.timestamp, datetime)
    
    def test_system_metrics_model(self):
        """Test SystemMetrics model validation"""
        metrics = SystemMetrics(
            requests_total=100,
            requests_per_minute=5.5,
            average_response_time_ms=250.0,
            error_rate_percent=2.5,
            cache_hit_rate_percent=75.0,
            active_connections=3
        )
        
        assert metrics.requests_total == 100
        assert metrics.requests_per_minute == 5.5
        assert metrics.error_rate_percent == 2.5


class TestPerformanceLogging:
    """Test performance logging functionality"""
    
    def test_request_logging(self):
        """Test request logging functionality"""
        monitor = PerformanceMonitor()
        
        # Create test metrics
        metrics = PerformanceMetrics(
            total_duration_ms=150.0,
            search_duration_ms=50.0,
            scraping_duration_ms=75.0,
            synthesis_duration_ms=25.0,
            sources_found=5,
            sources_scraped=4,
            sources_failed=1,
            cache_hits=2,
            cache_misses=3,
            timestamp=datetime.now()
        )
        
        # Test logging (should not raise exceptions)
        monitor.log_request("test query", metrics, success=True)
        monitor.log_request("failed query", metrics, success=False)
        
        # Verify no exceptions were raised
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])