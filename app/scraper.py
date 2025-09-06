import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.optimization_models import ContentQuality, EnhancedSource

def extract_main_content(soup: BeautifulSoup) -> Tuple[str, Dict[str, float]]:
    """
    Tries to find the main article content of a page, ignoring noise like
    nav bars, footers, and ads. It checks for common semantic tags.
    Returns both content and quality indicators.
    """
    quality_indicators = {}
    
    # Look for common main content containers in order of preference
    main_content = (
        soup.find('article') or 
        soup.find('main') or 
        soup.find('div', class_='post-content') or
        soup.find('div', class_='article-body') or
        soup.find('div', id='content')
    )
    
    # Track content extraction quality
    if main_content:
        content_text = main_content.get_text(separator=' ', strip=True)
        quality_indicators['semantic_container'] = 1.0
        
        # Check for structured content indicators
        paragraphs = main_content.find_all('p')
        headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        lists = main_content.find_all(['ul', 'ol'])
        
        quality_indicators['paragraph_count'] = len(paragraphs) / 10.0  # Normalize to 0-1
        quality_indicators['heading_structure'] = min(len(headings) / 5.0, 1.0)
        quality_indicators['list_structure'] = min(len(lists) / 3.0, 1.0)
        
    else:
        # As a fallback, use the whole body but it will be less clean.
        body = soup.find('body')
        content_text = body.get_text(separator=' ', strip=True) if body else ""
        quality_indicators['semantic_container'] = 0.3  # Lower quality for fallback
        quality_indicators['paragraph_count'] = 0.0
        quality_indicators['heading_structure'] = 0.0
        quality_indicators['list_structure'] = 0.0
    
    return content_text, quality_indicators

def extract_images(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Finds all significant images on the page and returns their absolute URLs
    and alt text.
    """
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
            
        # Convert relative URLs (e.g., /images/pic.jpg) to absolute URLs
        absolute_src = urljoin(base_url, src)
        
        # We only want content images, so we can filter out very small images or icons
        # A simple way is to ignore SVGs or very common non-content names.
        if absolute_src.endswith(('.svg', '.gif')):
            continue

        images.append({
            "src": absolute_src,
            "alt": img.get('alt', '')  # Get alt text, default to empty string
        })
    return images

def extract_categories(soup: BeautifulSoup) -> list[str]:
    """
    Finds categories, tags, or keywords from the page. It checks both
    meta tags and common HTML structures.
    """
    categories = set() # Use a set to avoid duplicates

    # 1. Check for <meta name="keywords">
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    if meta_keywords and meta_keywords.get('content'):
        keywords = [k.strip() for k in meta_keywords.get('content').split(',')]
        categories.update(keywords)

    # 2. Check for common class names for tags/categories
    for element in soup.find_all(['a', 'span'], class_=['category', 'tag', 'post-tag']):
        categories.add(element.get_text(strip=True))
        
    return list(categories)


def calculate_word_count(content: str) -> int:
    """Calculate word count from content text."""
    if not content:
        return 0
    # Split on whitespace and filter out empty strings
    words = [word for word in content.split() if word.strip()]
    return len(words)


def calculate_information_density(content: str, soup: BeautifulSoup) -> float:
    """
    Calculate information density as ratio of meaningful content to total page text.
    Higher density indicates better content quality.
    """
    if not content:
        return 0.0
    
    # Get total page text including navigation, ads, etc.
    total_text = soup.get_text(separator=' ', strip=True)
    
    if not total_text:
        return 0.0
    
    # Calculate density as ratio of main content to total content
    density = len(content) / len(total_text)
    return min(density, 1.0)  # Cap at 1.0


def detect_content_freshness(soup: BeautifulSoup) -> Tuple[Optional[datetime], float]:
    """
    Detect content freshness from page metadata and return last updated date and freshness score.
    Returns (last_updated_date, freshness_score) where freshness_score is 0.0-1.0.
    """
    last_updated = None
    freshness_score = 0.5  # Default neutral score
    
    # Common meta tags for publication/modification dates
    date_selectors = [
        ('meta[property="article:published_time"]', 'content'),
        ('meta[property="article:modified_time"]', 'content'),
        ('meta[name="date"]', 'content'),
        ('meta[name="pubdate"]', 'content'),
        ('meta[name="last-modified"]', 'content'),
        ('time[datetime]', 'datetime'),
        ('time[pubdate]', 'datetime'),
    ]
    
    for selector, attr in date_selectors:
        element = soup.select_one(selector)
        if element and element.get(attr):
            date_str = element.get(attr)
            try:
                # Try parsing ISO format first
                if 'T' in date_str:
                    last_updated = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                        try:
                            last_updated = datetime.strptime(date_str[:10], fmt)
                            break
                        except ValueError:
                            continue
                
                if last_updated:
                    # Calculate freshness score based on age
                    days_old = (datetime.now() - last_updated.replace(tzinfo=None)).days
                    if days_old <= 7:
                        freshness_score = 1.0
                    elif days_old <= 30:
                        freshness_score = 0.8
                    elif days_old <= 90:
                        freshness_score = 0.6
                    elif days_old <= 365:
                        freshness_score = 0.4
                    else:
                        freshness_score = 0.2
                    break
                    
            except (ValueError, TypeError):
                continue
    
    return last_updated, freshness_score


def extract_structured_data(soup: BeautifulSoup) -> Dict[str, any]:
    """
    Extract structured data from the page including JSON-LD, microdata, and other structured formats.
    """
    structured_data = {}
    
    # Extract JSON-LD structured data
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    if json_ld_scripts:
        import json
        json_ld_data = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                json_ld_data.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        structured_data['json_ld'] = json_ld_data
    
    # Extract Open Graph data
    og_data = {}
    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
    for tag in og_tags:
        property_name = tag.get('property', '').replace('og:', '')
        content = tag.get('content', '')
        if property_name and content:
            og_data[property_name] = content
    structured_data['open_graph'] = og_data
    
    # Extract Twitter Card data
    twitter_data = {}
    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
    for tag in twitter_tags:
        name = tag.get('name', '').replace('twitter:', '')
        content = tag.get('content', '')
        if name and content:
            twitter_data[name] = content
    structured_data['twitter_card'] = twitter_data
    
    # Extract basic meta description and author
    description_tag = soup.find('meta', attrs={'name': 'description'})
    if description_tag:
        structured_data['description'] = description_tag.get('content', '')
    
    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag:
        structured_data['author'] = author_tag.get('content', '')
    
    return structured_data


def calculate_content_relevance_score(content: str, query: str, title: str = "", categories: List[str] = None) -> float:
    """
    Calculate relevance score of content to the given query.
    Returns a score between 0.0 and 1.0.
    """
    if not content or not query:
        return 0.0
    
    categories = categories or []
    query_lower = query.lower()
    content_lower = content.lower()
    title_lower = title.lower()
    
    score = 0.0
    
    # Query terms in content (weighted by frequency)
    query_terms = [term.strip() for term in query_lower.split() if len(term.strip()) > 2]
    if query_terms:
        term_matches = 0
        for term in query_terms:
            # Count occurrences in content
            content_matches = content_lower.count(term)
            title_matches = title_lower.count(term) * 3  # Title matches weighted higher
            category_matches = sum(1 for cat in categories if term in cat.lower()) * 2
            
            term_matches += content_matches + title_matches + category_matches
        
        # Normalize by content length and query terms
        content_words = len(content.split())
        if content_words > 0:
            score += min(term_matches / (content_words * len(query_terms)) * 10, 0.6)
    
    # Exact phrase matching
    if query_lower in content_lower:
        score += 0.3
    
    # Title relevance bonus
    if any(term in title_lower for term in query_terms):
        score += 0.1
    
    return min(score, 1.0)

def scrape_url(url: str, query: str = "") -> Optional[Dict]:
    """
    Optimized scraping function that handles forbidden sites gracefully
    and provides faster processing with better error handling.
    """
    # Skip known problematic domains to save time
    forbidden_domains = [
        'gadgets360.com', 'amazon.in', 'jiomart.com', 
        'facebook.com', 'instagram.com', 'twitter.com',
        'linkedin.com', 'pinterest.com'
    ]
    
    # Quick domain check to skip forbidden sites
    for domain in forbidden_domains:
        if domain in url.lower():
            print(f"Skipping forbidden domain: {url}")
            return None
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    # Add headers to appear more like a real browser
    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    start_time = time.time()
    
    try:
        # Reduced timeout for faster processing
        response = scraper.get(url, timeout=10)
        
        # Handle specific error codes gracefully
        if response.status_code == 403:
            print(f"Access forbidden (403) for {url}")
            return None
        elif response.status_code == 404:
            print(f"Page not found (404) for {url}")
            return None
        elif response.status_code == 429:
            print(f"Rate limited (429) for {url}")
            return None
        
        response.raise_for_status()
        
        # Use faster parser for better performance
        soup = BeautifulSoup(response.content, 'lxml')
        
        title = soup.title.string.strip() if soup.title else "No Title Found"
        
        # Optimized content extraction - only get what we need
        main_content, quality_indicators = extract_main_content(soup)
        
        # Skip expensive operations for low-quality content
        if len(main_content) < 50:
            print(f"Skipping low-quality content from {url}")
            return None
        
        # Only extract additional data if content is substantial
        images = extract_images(soup, url) if len(main_content) > 500 else []
        categories = extract_categories(soup)
        
        # Optimized quality metrics calculation
        word_count = len(main_content.split())  # Faster word count
        information_density = min(word_count / len(main_content) * 100, 1.0) if main_content else 0.0
        
        # Skip expensive freshness detection for speed
        last_updated = None
        freshness_score = 0.5  # Default neutral score
        structured_data = None  # Skip for speed
        
        # Calculate relevance score if query provided
        relevance_score = 0.0
        if query:
            relevance_score = calculate_content_relevance_score(
                main_content, query, title, categories
            )
        
        # Add quality indicators for content assessment
        quality_indicators.update({
            'word_count_score': min(word_count / 500.0, 1.0),  # Normalize around 500 words
            'freshness_score': freshness_score,
            'relevance_score': relevance_score,
            'structured_data_present': 1.0 if structured_data else 0.0
        })
        
        # Create ContentQuality object
        content_quality = ContentQuality(
            relevance_score=relevance_score,
            content_length=word_count,
            information_density=information_density,
            duplicate_content=False,  # Will be set by content quality assessor
            quality_indicators=quality_indicators
        )
        
        scraping_duration = time.time() - start_time
        
        # Return enhanced data structure
        return {
            "url": url,
            "title": title,
            "main_content": main_content,
            "images": images,
            "categories": categories,
            "content_quality": content_quality,
            "scraping_duration": scraping_duration,
            "relevance_score": relevance_score,
            "word_count": word_count,
            "last_updated": last_updated,
            "structured_data": structured_data
        }

    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}")
        return None


def create_enhanced_source(scraped_data: Dict) -> Optional[EnhancedSource]:
    """
    Create an EnhancedSource object from scraped data.
    """
    if not scraped_data:
        return None
    
    try:
        return EnhancedSource(
            url=scraped_data["url"],
            title=scraped_data["title"],
            main_content=scraped_data["main_content"],
            images=scraped_data["images"],
            categories=scraped_data["categories"],
            content_quality=scraped_data.get("content_quality"),
            scraping_duration=scraped_data.get("scraping_duration"),
            relevance_score=scraped_data.get("relevance_score"),
            word_count=scraped_data.get("word_count"),
            last_updated=scraped_data.get("last_updated")
        )
    except Exception as e:
        print(f"Error creating EnhancedSource: {e}")
        return None
