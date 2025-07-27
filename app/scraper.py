import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_main_content(soup: BeautifulSoup) -> str:
    """
    Tries to find the main article content of a page, ignoring noise like
    nav bars, footers, and ads. It checks for common semantic tags.
    """
    # Look for common main content containers in order of preference
    main_content = (
        soup.find('article') or 
        soup.find('main') or 
        soup.find('div', class_='post-content') or
        soup.find('div', class_='article-body') or
        soup.find('div', id='content')
    )
    
    # If a specific container is found, get text from it.
    if main_content:
        return main_content.get_text(separator=' ', strip=True)
    
    # As a fallback, use the whole body but it will be less clean.
    body = soup.find('body')
    return body.get_text(separator=' ', strip=True) if body else ""

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

def scrape_url(url: str):
    """
    Scrapes a URL for its title, main content, images, and categories
    using cloudscraper to bypass advanced bot detection.
    """
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "No Title Found"
        
        # Use our new helper functions to extract structured data
        main_content = extract_main_content(soup)
        images = extract_images(soup, url)
        categories = extract_categories(soup)
        
        # Return a much richer dictionary of information
        return {
            "url": url,
            "title": title,
            "main_content": main_content,
            "images": images,
            "categories": categories
        }

    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}")
        return None
