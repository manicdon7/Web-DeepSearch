import cloudscraper # Import cloudscraper instead of requests
from bs4 import BeautifulSoup

def scrape_url(url: str):
    """
    Scrapes a URL using cloudscraper to bypass advanced bot detection systems
    like Cloudflare, extracting the page title and all visible text.
    """
    # Create a scraper instance. It mimics a real browser.
    scraper = cloudscraper.create_scraper()
    
    try:
        # Use scraper.get() which has the same syntax as requests.get()
        response = scraper.get(url, timeout=20)
        
        # Cloudscraper handles the challenge, but we still check the final status
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.title.string if soup.title else "No Title Found"
        
        body = soup.find('body')
        if body:
            full_text = body.get_text(separator=' ', strip=True)
        else:
            full_text = "No main content found."
        
        return {
            "url": url,
            "title": title,
            "content": full_text
        }

    except Exception as e:
        # This will catch network errors or if the status code is still an error
        print(f"Error fetching {url}: {e}")
        return None
