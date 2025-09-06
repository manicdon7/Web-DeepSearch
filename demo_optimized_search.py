#!/usr/bin/env python3
"""
Demonstration script for the optimized search client.
Shows the difference between the legacy and optimized search approaches.
"""

import time
import logging
from app.search_client import OptimizedSearchClient, search_and_scrape_multiple_sources

# Configure logging to see the optimization in action
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def demo_optimized_search():
    """Demonstrate the optimized search client capabilities."""
    print("=== Optimized Search Client Demo ===\n")
    
    # Initialize the optimized client
    client = OptimizedSearchClient(
        max_concurrent=3,
        timeout_per_source=8,
        max_sources=10,
        enable_early_termination=True
    )
    
    # Test queries with different characteristics
    test_queries = [
        "What is Python programming?",  # Simple factual query
        "Python vs JavaScript comparison for web development",  # Complex comparison query
        "How to implement machine learning algorithms in Python",  # How-to query
        "Latest Python 3.12 features and updates 2024"  # News/recent query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i}: '{query}' ---")
        
        # Time the optimized search
        start_time = time.time()
        try:
            results = client.search_and_scrape_multiple_sources(query)
            optimized_time = time.time() - start_time
            
            print(f"✅ Optimized search completed in {optimized_time:.2f} seconds")
            print(f"📊 Found {len(results)} high-quality sources")
            
            # Show cache statistics
            cache_stats = client.get_cache_statistics()
            print(f"💾 Cache: {cache_stats['size']} entries, "
                  f"{cache_stats['statistics']['hit_rate']:.1f}% hit rate")
            
            # Show first result as example
            if results:
                first_result = results[0]
                title = first_result.get('title', 'No title')[:60]
                content_length = len(first_result.get('main_content', '').split())
                print(f"📄 First result: '{title}...' ({content_length} words)")
            
        except Exception as e:
            print(f"❌ Error in optimized search: {e}")
        
        print("-" * 60)

def demo_performance_comparison():
    """Compare performance between legacy and optimized approaches."""
    print("\n=== Performance Comparison Demo ===\n")
    
    test_query = "Python machine learning tutorial"
    
    # Test legacy approach
    print("Testing legacy search approach...")
    start_time = time.time()
    try:
        legacy_results = search_and_scrape_multiple_sources(test_query)
        legacy_time = time.time() - start_time
        print(f"Legacy search: {len(legacy_results)} results in {legacy_time:.2f}s")
    except Exception as e:
        print(f"Legacy search error: {e}")
        legacy_time = float('inf')
        legacy_results = []
    
    # Test optimized approach
    print("\nTesting optimized search approach...")
    client = OptimizedSearchClient(max_concurrent=5, max_sources=15)
    start_time = time.time()
    try:
        optimized_results = client.search_and_scrape_multiple_sources(test_query)
        optimized_time = time.time() - start_time
        print(f"Optimized search: {len(optimized_results)} results in {optimized_time:.2f}s")
    except Exception as e:
        print(f"Optimized search error: {e}")
        optimized_time = float('inf')
        optimized_results = []
    
    # Compare results
    if legacy_time != float('inf') and optimized_time != float('inf'):
        speedup = legacy_time / optimized_time if optimized_time > 0 else 0
        print(f"\n📈 Performance improvement: {speedup:.1f}x faster")
        print(f"⏱️  Time saved: {legacy_time - optimized_time:.2f} seconds")
    
    print(f"📊 Quality comparison:")
    print(f"   Legacy: {len(legacy_results)} sources")
    print(f"   Optimized: {len(optimized_results)} sources (intelligently selected)")

def demo_caching_benefits():
    """Demonstrate caching benefits with repeated queries."""
    print("\n=== Caching Benefits Demo ===\n")
    
    client = OptimizedSearchClient()
    test_query = "Python data science libraries"
    
    # First search (cold cache)
    print("First search (cold cache)...")
    start_time = time.time()
    results1 = client.search_and_scrape_multiple_sources(test_query)
    first_time = time.time() - start_time
    
    cache_stats = client.get_cache_statistics()
    print(f"First search: {len(results1)} results in {first_time:.2f}s")
    print(f"Cache after first search: {cache_stats['size']} entries")
    
    # Second search (warm cache)
    print("\nSecond search (warm cache)...")
    start_time = time.time()
    results2 = client.search_and_scrape_multiple_sources(test_query)
    second_time = time.time() - start_time
    
    cache_stats = client.get_cache_statistics()
    print(f"Second search: {len(results2)} results in {second_time:.2f}s")
    print(f"Cache hit rate: {cache_stats['statistics']['hit_rate']:.1f}%")
    
    if first_time > 0 and second_time > 0:
        speedup = first_time / second_time
        print(f"🚀 Cache speedup: {speedup:.1f}x faster on repeated query")

if __name__ == "__main__":
    try:
        demo_optimized_search()
        demo_performance_comparison()
        demo_caching_benefits()
        
        print("\n🎉 Demo completed successfully!")
        print("\nKey optimizations demonstrated:")
        print("✅ Intelligent source ranking and selection")
        print("✅ Concurrent scraping with early termination")
        print("✅ Content quality assessment and filtering")
        print("✅ Caching for improved performance")
        print("✅ Adaptive behavior based on query analysis")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")