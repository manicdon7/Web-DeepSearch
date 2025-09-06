try:
    from pollinations.helpers import version_check
    version_check.get_latest = lambda: None
    print("Successfully applied monkey patch to pollinations.ai.")
except (ImportError, AttributeError):
    # For now, we assume it exists and proceed.
    print("Could not apply patch to pollinations.ai. Proceeding with caution.")

import logging
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .model import QueryRequest, QueryResponse, HealthCheckResponse, SystemMetrics, PerformanceMetrics
from .config import settings
from .performance_monitor import performance_monitor, RequestTimer
from . import search_client

# Configure logging first
logging.basicConfig(
    level=getattr(logging, settings.optimization.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agent module (now handles pollinations compatibility internally)
from . import agent

app = FastAPI(
    title="Multi-Source Research Agent API",
    description="An optimized API that searches the web, scrapes multiple sources, and synthesizes comprehensive answers with intelligent performance monitoring.",
    version="1.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def performance_monitoring_middleware(request: Request, call_next):
    """Middleware to track performance metrics for all requests"""
    start_time = performance_monitor.record_request_start()
    
    try:
        response = await call_next(request)
        performance_monitor.record_request_end(start_time, success=True)
        return response
    except Exception as e:
        performance_monitor.record_request_end(start_time, success=False)
        logger.error(f"Request failed: {str(e)}")
        raise

@app.post("/query/", response_model=QueryResponse, summary="Get a synthesized answer from multiple web sources")
async def process_query(request: QueryRequest):
    """
    Accepts a search query, finds and scrapes multiple relevant web pages,
    and returns a single, AI-synthesized answer based on all gathered content.
    Now with intelligent optimization and performance monitoring.
    """
    query = request.query
    logger.info(f"Processing optimized query: '{query}'")
    
    # Initialize request timer for detailed performance tracking
    timer = RequestTimer().start_request()
    
    try:
        # Step 1: Search and intelligently scrape multiple sources
        with timer.time_phase("search"):
            scraped_sources = search_client.search_and_scrape_multiple_sources(query)
        
        logger.info(f"Scraped {len(scraped_sources)} sources")
        
        if not scraped_sources:
            raise HTTPException(
                status_code=404, 
                detail="Could not find and scrape any relevant web pages for the query."
            )

        # Step 2: Generate adaptive synthesized answer
        with timer.time_phase("synthesis"):
            answer = agent.get_ai_synthesis(query, scraped_sources)
        
        if answer == "Could not generate an answer.":
            raise HTTPException(
                status_code=500, 
                detail="Content was scraped, but the AI agent failed to generate an answer."
            )
        
        # Step 3: Prepare performance metrics and response
        source_urls = [source['url'] for source in scraped_sources]
        
        # Create performance metrics (these would be populated by the optimization components)
        # For now, using placeholder values that would come from the actual optimization components
        performance_metrics = timer.create_performance_metrics(
            sources_found=len(source_urls),
            sources_scraped=len(scraped_sources),
            sources_failed=0,  # This would be tracked by the concurrent scraper
            cache_hits=0,      # This would be tracked by the cache manager
            cache_misses=0     # This would be tracked by the cache manager
        )
        
        # Log the request for analysis
        performance_monitor.log_request(query, performance_metrics, success=True)
        
        logger.info(f"Successfully generated optimized answer in {performance_metrics.total_duration_ms:.2f}ms")
        
        response = QueryResponse(
            answer=answer, 
            sources_used=source_urls,
            performance_metrics=performance_metrics if settings.optimization.enable_performance_monitoring else None
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing query '{query}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your query."
        )

@app.get("/", summary="Root endpoint")
async def read_root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to the Optimized Multi-Source Research Agent API!",
        "version": "5.0.0",
        "features": [
            "Intelligent source ranking",
            "Concurrent scraping",
            "Adaptive summary generation",
            "Performance monitoring",
            "Caching optimization"
        ]
    }

@app.get("/health", response_model=HealthCheckResponse, summary="Comprehensive health check")
async def health_check():
    """
    Comprehensive health check endpoint that provides system status,
    performance metrics, and component health information.
    """
    try:
        # Get system metrics
        system_metrics = performance_monitor.get_system_metrics()
        uptime = performance_monitor.get_uptime()
        
        # Get system resource information
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
        
        # Check component status (placeholder - would integrate with actual components)
        component_status = {
            "search_client": "healthy",
            "ai_agent": "healthy",
            "cache_manager": "healthy",
            "concurrent_scraper": "healthy",
            "query_analyzer": "healthy",
            "source_ranker": "healthy"
        }
        
        # Determine overall status
        overall_status = "healthy"
        if cpu_percent > 90 or memory.percent > 90:
            overall_status = "degraded"
        if system_metrics.error_rate_percent > 10:
            overall_status = "unhealthy"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            version="5.0.0",
            uptime_seconds=uptime,
            system_metrics=system_info,
            component_status=component_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="5.0.0",
            uptime_seconds=performance_monitor.get_uptime(),
            system_metrics={},
            component_status={"error": str(e)}
        )

@app.get("/metrics", response_model=SystemMetrics, summary="Performance metrics")
async def get_metrics():
    """
    Get current system performance metrics including request rates,
    response times, error rates, and cache performance.
    """
    return performance_monitor.get_system_metrics()

@app.get("/ping", summary="Simple health check endpoint")
async def ping():
    """Simple ping endpoint for basic health checks"""
    return {"status": "ok", "message": "pong", "timestamp": datetime.now()}

@app.get("/config", summary="Get current optimization configuration")
async def get_config():
    """
    Get current optimization configuration parameters.
    Useful for monitoring and debugging performance settings.
    """
    return {
        "optimization_settings": {
            "max_concurrent_scrapers": settings.optimization.max_concurrent_scrapers,
            "scraper_timeout_seconds": settings.optimization.scraper_timeout_seconds,
            "max_sources_to_scrape": settings.optimization.max_sources_to_scrape,
            "cache_ttl_seconds": settings.optimization.cache_ttl_seconds,
            "enable_caching": settings.optimization.enable_caching,
            "enable_performance_monitoring": settings.optimization.enable_performance_monitoring,
            "min_content_quality_score": settings.optimization.min_content_quality_score,
            "min_relevance_score": settings.optimization.min_relevance_score
        }
    }
