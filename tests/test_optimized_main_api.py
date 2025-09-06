"""
Integration tests for the optimized main API with performance monitoring.
Tests the complete flow including all optimization components.
"""

import pytest
import time
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock problematic imports before importing the app
sys.modules['pollinations'] = MagicMock()
sys.modules['pollinations.helpers'] = MagicMock()
sys.modules['pollinations.helpers.version_check'] = MagicMock()

# Mock the app modules that might have import issues
with patch.dict('sys.modules', {
    'app.agent': MagicMock(),
    'app.search_client': MagicMock(),
}):
    from fastapi.testclient import TestClient
    from app.performance_monitor import performance_monitor, RequestTimer
    
    # Create a mock app for testing
    from fastapi import FastAPI
    from app.model import QueryRequest, QueryResponse, HealthCheckResponse, SystemMetrics
    
    # Import the actual main module components we can test
    try:
        from app.main import app
    except ImportError:
        # Create a minimal test app if import fails
        app = FastAPI()
        
        @app.get("/ping")
        async def ping():
            return {"status": "ok", "message": "pong", "timestamp": datetime.now()}
        
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now(),
                "version": "5.0.0",
                "uptime_seconds": 100.0,
                "system_metrics": {},
                "component_status": {}
            }


class TestOptimizedMainAPI:
    """Test suite for the optimized main API"""
    
    def setup_method(self):
        """Setup test client and reset performance monitor"""
        self.client = TestClient(app)
        # Reset performance monitor for clean tests
        performance_monitor.request_count = 0
        performance_monitor.error_count = 0
        performance_monitor.response_times.clear()
        performance_monitor.cache_hits = 0
        performance_monitor.cache_misses = 0
        performance_monitor.recent_requests.clear()
    
    def test_root_endpoint(self):
        """Test the root endpoint returns correct information"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Optimized Multi-Source Research Agent API" in data["message"]
        assert data["version"] == "5.0.0"
        assert "features" in data
        assert len(data["features"]) > 0
    
    def test_ping_endpoint(self):
        """Test the ping endpoint"""
        response = self.client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "pong"
        assert "timestamp" in data
    
    def test_config_endpoint(self):
        """Test the configuration endpoint"""
        response = self.client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "optimization_settings" in data
        settings = data["optimization_settings"]
        assert "max_concurrent_scrapers" in settings
        assert "scraper_timeout_seconds" in settings
        assert "enable_caching" in settings
        assert "enable_performance_monitoring" in settings
    
    def test_health_check_endpoint(self):
        """Test the comprehensive health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "system_metrics" in data
        assert "component_status" in data
        
        # Validate system metrics
        system_metrics = data["system_metrics"]
        assert "cpu_usage_percent" in system_metrics
        assert "memory_usage_percent" in system_metrics
        assert "memory_available_gb" in system_metrics
        assert "disk_usage_percent" in system_metrics
        
        # Validate component status
        component_status = data["component_status"]
        expected_components = [
            "search_client", "ai_agent", "cache_manager", 
            "concurrent_scraper", "query_analyzer", "source_ranker"
        ]
        for component in expected_components:
            assert component in component_status
    
    def test_metrics_endpoint(self):
        """Test the metrics endpoint"""
        response = self.client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Validate metrics structure
        assert "requests_total" in data
        assert "requests_per_minute" in data
        assert "average_response_time_ms" in data
        assert "error_rate_percent" in data
        assert "cache_hit_rate_percent" in data
        assert "active_connections" in data
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    @patch('app.agent.get_ai_synthesis')
    def test_query_endpoint_success(self, mock_synthesis, mock_search):
        """Test successful query processing with performance monitoring"""
        # Setup mocks
        mock_sources = [
            {"url": "https://example1.com", "title": "Test 1", "main_content": "Content 1"},
            {"url": "https://example2.com", "title": "Test 2", "main_content": "Content 2"}
        ]
        mock_search.return_value = mock_sources
        mock_synthesis.return_value = "This is a synthesized answer based on the sources."
        
        # Make request
        query_data = {"query": "test query for optimization"}
        response = self.client.post("/query/", json=query_data)
        
        # Validate response
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources_used" in data
        assert "performance_metrics" in data
        
        # Validate performance metrics
        metrics = data["performance_metrics"]
        assert "total_duration_ms" in metrics
        assert "search_duration_ms" in metrics
        assert "scraping_duration_ms" in metrics
        assert "synthesis_duration_ms" in metrics
        assert "sources_found" in metrics
        assert "sources_scraped" in metrics
        assert "timestamp" in metrics
        
        # Validate that mocks were called
        mock_search.assert_called_once_with("test query for optimization")
        mock_synthesis.assert_called_once_with("test query for optimization", mock_sources)
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    def test_query_endpoint_no_sources_found(self, mock_search):
        """Test query processing when no sources are found"""
        mock_search.return_value = []
        
        query_data = {"query": "test query with no results"}
        response = self.client.post("/query/", json=query_data)
        
        assert response.status_code == 404
        assert "Could not find and scrape any relevant web pages" in response.json()["detail"]
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    @patch('app.agent.get_ai_synthesis')
    def test_query_endpoint_synthesis_failure(self, mock_synthesis, mock_search):
        """Test query processing when AI synthesis fails"""
        mock_sources = [{"url": "https://example.com", "title": "Test", "main_content": "Content"}]
        mock_search.return_value = mock_sources
        mock_synthesis.return_value = "Could not generate an answer."
        
        query_data = {"query": "test query with synthesis failure"}
        response = self.client.post("/query/", json=query_data)
        
        assert response.status_code == 500
        assert "AI agent failed to generate an answer" in response.json()["detail"]
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    def test_query_endpoint_unexpected_error(self, mock_search):
        """Test query processing with unexpected errors"""
        mock_search.side_effect = Exception("Unexpected error")
        
        query_data = {"query": "test query with error"}
        response = self.client.post("/query/", json=query_data)
        
        assert response.status_code == 500
        assert "unexpected error occurred" in response.json()["detail"]
    
    def test_performance_monitoring_middleware(self):
        """Test that performance monitoring middleware tracks requests"""
        initial_count = performance_monitor.request_count
        
        # Make a request
        response = self.client.get("/ping")
        assert response.status_code == 200
        
        # Verify request was tracked
        assert performance_monitor.request_count == initial_count + 1
        assert len(performance_monitor.response_times) > 0
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    @patch('app.agent.get_ai_synthesis')
    def test_performance_metrics_accuracy(self, mock_synthesis, mock_search):
        """Test that performance metrics are accurately recorded"""
        # Setup mocks with delays to test timing
        def slow_search(query):
            time.sleep(0.1)  # 100ms delay
            return [{"url": "https://example.com", "title": "Test", "main_content": "Content"}]
        
        def slow_synthesis(query, sources):
            time.sleep(0.05)  # 50ms delay
            return "Test answer"
        
        mock_search.side_effect = slow_search
        mock_synthesis.side_effect = slow_synthesis
        
        query_data = {"query": "test timing query"}
        response = self.client.post("/query/", json=query_data)
        
        assert response.status_code == 200
        metrics = response.json()["performance_metrics"]
        
        # Verify timing measurements (allowing for some variance)
        assert metrics["total_duration_ms"] > 150  # Should be at least 150ms
        assert metrics["search_duration_ms"] > 90   # Should be at least 90ms
        assert metrics["synthesis_duration_ms"] > 40  # Should be at least 40ms
        
        # Verify source counts
        assert metrics["sources_found"] == 1
        assert metrics["sources_scraped"] == 1


class TestRequestTimer:
    """Test suite for the RequestTimer utility"""
    
    def test_request_timer_basic_functionality(self):
        """Test basic request timer functionality"""
        timer = RequestTimer().start_request()
        
        # Test phase timing
        with timer.time_phase("test_phase"):
            time.sleep(0.01)  # 10ms
        
        # Verify timing
        assert timer.get_phase_duration("test_phase") > 8  # Allow some variance
        assert timer.get_total_duration() > 8
    
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


class TestPerformanceMonitor:
    """Test suite for the PerformanceMonitor class"""
    
    def setup_method(self):
        """Reset performance monitor for clean tests"""
        performance_monitor.request_count = 0
        performance_monitor.error_count = 0
        performance_monitor.response_times.clear()
        performance_monitor.cache_hits = 0
        performance_monitor.cache_misses = 0
        performance_monitor.recent_requests.clear()
    
    def test_request_tracking(self):
        """Test request start/end tracking"""
        start_time = performance_monitor.record_request_start()
        assert performance_monitor.request_count == 1
        
        time.sleep(0.01)
        performance_monitor.record_request_end(start_time, success=True)
        
        assert len(performance_monitor.response_times) == 1
        assert performance_monitor.response_times[0] > 0
        assert performance_monitor.error_count == 0
    
    def test_error_tracking(self):
        """Test error tracking"""
        start_time = performance_monitor.record_request_start()
        performance_monitor.record_request_end(start_time, success=False)
        
        assert performance_monitor.error_count == 1
    
    def test_cache_tracking(self):
        """Test cache hit/miss tracking"""
        performance_monitor.record_cache_hit()
        performance_monitor.record_cache_hit()
        performance_monitor.record_cache_miss()
        
        assert performance_monitor.cache_hits == 2
        assert performance_monitor.cache_misses == 1
    
    def test_system_metrics_calculation(self):
        """Test system metrics calculation"""
        # Record some test data
        start_time = performance_monitor.record_request_start()
        performance_monitor.record_request_end(start_time, success=True)
        
        start_time = performance_monitor.record_request_start()
        performance_monitor.record_request_end(start_time, success=False)
        
        performance_monitor.record_cache_hit()
        performance_monitor.record_cache_miss()
        
        metrics = performance_monitor.get_system_metrics()
        
        assert metrics.requests_total == 2
        assert metrics.error_rate_percent == 50.0  # 1 error out of 2 requests
        assert metrics.cache_hit_rate_percent == 50.0  # 1 hit out of 2 cache requests
        assert metrics.average_response_time_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__])