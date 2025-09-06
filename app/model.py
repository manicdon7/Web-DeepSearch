from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class CrawlRequest(BaseModel):
    url: HttpUrl

class SearchResult(BaseModel):
    url: HttpUrl
    title: str
    summary: str

# --- Models for Query-Based Searching (Updated) ---
class QueryRequest(BaseModel):
    query: str

class PerformanceMetrics(BaseModel):
    """Performance metrics for a query request"""
    total_duration_ms: float
    search_duration_ms: float
    scraping_duration_ms: float
    synthesis_duration_ms: float
    sources_found: int
    sources_scraped: int
    sources_failed: int
    cache_hits: int
    cache_misses: int
    timestamp: datetime

class QueryResponse(BaseModel):
    """The final response, including the AI-generated answer and sources."""
    answer: str
    sources_used: List[HttpUrl]
    performance_metrics: Optional[PerformanceMetrics] = None

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    system_metrics: Dict[str, Any]
    component_status: Dict[str, str]

class SystemMetrics(BaseModel):
    """System performance metrics"""
    requests_total: int
    requests_per_minute: float
    average_response_time_ms: float
    error_rate_percent: float
    cache_hit_rate_percent: float
    active_connections: int
