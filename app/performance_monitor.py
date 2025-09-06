"""
Performance monitoring and metrics collection for the search optimization API.
"""

import time
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from threading import Lock
from contextlib import contextmanager

from .model import PerformanceMetrics, SystemMetrics

class PerformanceMonitor:
    """Tracks and manages performance metrics for the API"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.cache_hits = 0
        self.cache_misses = 0
        self.recent_requests = deque(maxlen=100)  # Keep last 100 request timestamps
        self._lock = Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def record_request_start(self) -> float:
        """Record the start of a request and return start time"""
        start_time = time.time()
        with self._lock:
            self.request_count += 1
            self.recent_requests.append(datetime.now())
        return start_time
    
    def record_request_end(self, start_time: float, success: bool = True):
        """Record the end of a request"""
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        with self._lock:
            self.response_times.append(duration)
            if not success:
                self.error_count += 1
    
    def record_cache_hit(self):
        """Record a cache hit"""
        with self._lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        with self._lock:
            self.cache_misses += 1
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics"""
        with self._lock:
            # Calculate requests per minute
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            recent_count = sum(1 for req_time in self.recent_requests if req_time > one_minute_ago)
            
            # Calculate average response time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            # Calculate error rate
            error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
            
            # Calculate cache hit rate
            total_cache_requests = self.cache_hits + self.cache_misses
            cache_hit_rate = (self.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0
            
            return SystemMetrics(
                requests_total=self.request_count,
                requests_per_minute=recent_count,
                average_response_time_ms=avg_response_time,
                error_rate_percent=error_rate,
                cache_hit_rate_percent=cache_hit_rate,
                active_connections=0  # This would need to be tracked separately
            )
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time
    
    def log_request(self, query: str, metrics: PerformanceMetrics, success: bool = True):
        """Log request details for analysis"""
        log_level = logging.INFO if success else logging.ERROR
        self.logger.log(
            log_level,
            f"Query processed: '{query[:50]}...' | "
            f"Duration: {metrics.total_duration_ms:.2f}ms | "
            f"Sources: {metrics.sources_scraped}/{metrics.sources_found} | "
            f"Cache: {metrics.cache_hits}H/{metrics.cache_misses}M | "
            f"Success: {success}"
        )

class RequestTimer:
    """Context manager for timing different phases of request processing"""
    
    def __init__(self):
        self.timings = {}
        self.start_time = None
        self.current_phase = None
    
    def start_request(self):
        """Start timing the overall request"""
        self.start_time = time.time()
        return self
    
    @contextmanager
    def time_phase(self, phase_name: str):
        """Time a specific phase of processing"""
        phase_start = time.time()
        self.current_phase = phase_name
        try:
            yield
        finally:
            phase_duration = (time.time() - phase_start) * 1000  # Convert to ms
            self.timings[phase_name] = phase_duration
            self.current_phase = None
    
    def get_total_duration(self) -> float:
        """Get total request duration in milliseconds"""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000
    
    def get_phase_duration(self, phase_name: str) -> float:
        """Get duration of a specific phase in milliseconds"""
        return self.timings.get(phase_name, 0.0)
    
    def create_performance_metrics(self, sources_found: int, sources_scraped: int, 
                                 sources_failed: int, cache_hits: int, cache_misses: int) -> PerformanceMetrics:
        """Create a PerformanceMetrics object from collected timings"""
        return PerformanceMetrics(
            total_duration_ms=self.get_total_duration(),
            search_duration_ms=self.get_phase_duration("search"),
            scraping_duration_ms=self.get_phase_duration("scraping"),
            synthesis_duration_ms=self.get_phase_duration("synthesis"),
            sources_found=sources_found,
            sources_scraped=sources_scraped,
            sources_failed=sources_failed,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            timestamp=datetime.now()
        )

# Global performance monitor instance
performance_monitor = PerformanceMonitor()