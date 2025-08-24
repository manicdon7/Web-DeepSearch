from ddgs import DDGS
from . import scraper

DOMAIN_BLOCKLIST = [
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "vimeo.com",
    "dailymotion.com",
    "pornhub.com",
    "xvideos.com",
    "xnxx.com",
    "ebay.com",
    "aliexpress.com",
    "fandom.com"
]

def search_and_scrape_multiple_sources(query: str) -> list[dict]:
    """
    Performs a web search, scrapes all available pages, and returns their content.
    
    Args:
        query: The user's search query.
    
    Returns:
        A list of dictionaries, where each dict contains the scraped data.
    """
    scraped_sources = []
    try:
        with DDGS() as ddgs:
            # Fetch as many results as possible
            search_results = list(ddgs.text(query, max_results=50))

            if not search_results:
                print("No search results found.")
                return []

            # Iterate through all results and scrape all valid sources
            for result in search_results:
                url = result['href']
                
                if any(blocked_domain in url for blocked_domain in DOMAIN_BLOCKLIST):
                    print(f"Skipping blocked domain: {url}")
                    continue

                print(f"Attempting to scrape: {url}")
                scraped_data = scraper.scrape_url(url)
                
                if scraped_data and scraped_data["main_content"].strip():
                    print(f"Successfully scraped: {url}")
                    scraped_sources.append(scraped_data)
            
            # Return all scraped sources without artificial limits
            return scraped_sources

    except Exception as e:
        print(f"An error occurred during web search: {e}")
        return []
