from typing import List, Tuple
from urllib.parse import urlsplit

from sources import Offer, HANDLERS


def test_query(url: str, limit: int = 5) -> Tuple[List[Offer], bool]:
    """
    Test a search query and return a limited number of offers.
    This is used for previewing results before saving a query.
    Returns a tuple of (offers, has_more_results).
    """
    try:
        split = urlsplit(url)
        if split.netloc not in HANDLERS:
            raise ValueError(f"Unsupported site: {split.netloc}")
        
        handler = HANDLERS[split.netloc]
        offers = handler(url, max_pages=1)  # Only fetch first page for testing
        
        # Check if there might be more results
        has_more_results = len(offers) > limit
        
        # Return only the first 'limit' offers for preview
        return offers[:limit], has_more_results
        
    except Exception as e:
        raise Exception(f"Error testing query: {str(e)}")


def scrape_query(url: str) -> List[Offer]:
    """
    Scrape all offers from a query URL.
    This is used for the full scraping process.
    """
    try:
        split = urlsplit(url)
        if split.netloc not in HANDLERS:
            raise ValueError(f"Unsupported site: {split.netloc}")
        
        handler = HANDLERS[split.netloc]
        return handler(url)  # Fetch all pages for full scraping
        
    except Exception as e:
        raise Exception(f"Error scraping query: {str(e)}")


def get_supported_sites() -> List[str]:
    """Return a list of supported sites."""
    return list(HANDLERS.keys())
