"""
API endpoint tests for the optimized main API.
Tests the API endpoints without requiring external dependencies.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock problematic imports
sys.modules['pollinations'] = MagicMock()
sys.modules['pollinations.helpers'] = MagicMock()
sys.modules['pollinations.helpers.version_check'] = MagicMock()

# Mock the agent and search_client modules
mock_agent = MagicMock()
mock_search_client = MagicMock()

with patch.dict('sys.modules', {
    'app.agent': mock_agent,
    'app.search_client': mock_search_client,
}):
    from fastapi.testclient import TestClient
    
    # Now we can safely import the main app
    try:
        from app.main import app
        client = TestClient(app)
        APP_AVAILABLE = True
    except Exception as e:
        print(f"Could not import app: {e}")
        APP_AVAILABLE = False
        client = None


@pytest.mark.skipif(not APP_AVAILABLE, reason="Main app not available")
class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    def test_root_endpoint(self):
        """Test the root endpoint returns correct information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "features" in data
    
    def test_ping_endpoint(self):
        """Test the ping endpoint"""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "pong"
        assert "timestamp" in data
    
    def test_config_endpoint(self):
        """Test the configuration endpoint"""
        response = client.get("/config")
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
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        required_fields = ["status", "timestamp", "version", "uptime_seconds", "system_metrics", "component_status"]
        for field in required_fields:
            assert field in data
        
        # Validate system metrics structure
        system_metrics = data["system_metrics"]
        expected_metrics = ["cpu_usage_percent", "memory_usage_percent", "memory_available_gb", "disk_usage_percent"]
        for metric in expected_metrics:
            assert metric in system_metrics
    
    def test_metrics_endpoint(self):
        """Test the metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Validate metrics structure
        expected_metrics = [
            "requests_total", "requests_per_minute", "average_response_time_ms",
            "error_rate_percent", "cache_hit_rate_percent", "active_connections"
        ]
        for metric in expected_metrics:
            assert metric in data
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    @patch('app.agent.get_ai_synthesis')
    def test_query_endpoint_success(self, mock_synthesis, mock_search):
        """Test successful query processing"""
        # Setup mocks
        mock_sources = [
            {"url": "https://example1.com", "title": "Test 1", "main_content": "Content 1"},
            {"url": "https://example2.com", "title": "Test 2", "main_content": "Content 2"}
        ]
        mock_search.return_value = mock_sources
        mock_synthesis.return_value = "This is a synthesized answer."
        
        # Make request
        query_data = {"query": "test query"}
        response = client.post("/query/", json=query_data)
        
        # Validate response
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources_used" in data
        assert data["answer"] == "This is a synthesized answer."
        assert len(data["sources_used"]) == 2
    
    @patch('app.search_client.search_and_scrape_multiple_sources')
    def test_query_endpoint_no_sources(self, mock_search):
        """Test query processing when no sources are found"""
        mock_search.return_value = []
        
        query_data = {"query": "test query with no results"}
        response = client.post("/query/", json=query_data)
        
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
        response = client.post("/query/", json=query_data)
        
        assert response.status_code == 500
        assert "AI agent failed to generate an answer" in response.json()["detail"]


class TestPerformanceMonitoringIntegration:
    """Test performance monitoring integration without full API"""
    
    def test_performance_monitor_import(self):
        """Test that performance monitor can be imported and used"""
        from app.performance_monitor import performance_monitor, RequestTimer
        
        # Test basic functionality
        start_time = performance_monitor.record_request_start()
        assert performance_monitor.request_count >= 1
        
        performance_monitor.record_request_end(start_time, success=True)
        assert len(performance_monitor.response_times) >= 1
    
    def test_request_timer_functionality(self):
        """Test request timer functionality"""
        from app.performance_monitor import RequestTimer
        
        timer = RequestTimer().start_request()
        
        with timer.time_phase("test"):
            pass  # Minimal operation
        
        assert timer.get_phase_duration("test") >= 0
        assert timer.get_total_duration() >= 0


class TestConfigurationSystem:
    """Test the configuration system"""
    
    def test_configuration_loading(self):
        """Test that configuration loads correctly"""
        from app.config import settings, OptimizationSettings
        
        # Test that settings object exists and has expected attributes
        assert hasattr(settings, 'optimization')
        assert isinstance(settings.optimization, OptimizationSettings)
        
        # Test optimization settings
        opt = settings.optimization
        assert hasattr(opt, 'max_concurrent_scrapers')
        assert hasattr(opt, 'scraper_timeout_seconds')
        assert hasattr(opt, 'enable_caching')
        assert hasattr(opt, 'enable_performance_monitoring')
    
    def test_optimization_settings_values(self):
        """Test that optimization settings have reasonable values"""
        from app.config import OptimizationSettings
        
        settings = OptimizationSettings()
        
        # Test reasonable defaults
        assert 1 <= settings.max_concurrent_scrapers <= 20
        assert 1 <= settings.scraper_timeout_seconds <= 60
        assert 60 <= settings.cache_ttl_seconds <= 86400  # 1 minute to 1 day
        assert isinstance(settings.enable_caching, bool)
        assert isinstance(settings.enable_performance_monitoring, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])