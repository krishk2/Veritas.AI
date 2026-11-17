import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup
from veritas.core.interfaces import IContentFetcher

logger = logging.getLogger("veritas.fetcher_service")

class HtmlContentFetcher:
    """Standard HTTP content fetcher with browser emulation and DOM cleaning."""
    
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.headers = {
            "User-Agent": user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def fetch_and_clean(self, url: str) -> Optional[str]:
        if not url:
            return None

        # Skip heavy social media/video domains that block static HTTP scrapers
        if any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com"]):
            return None

        try:
            response = requests.get(url, headers=self.headers, timeout=(3.0, 5.0))
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, "html.parser")
            
            # Decompose irrelevant nodes
            for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                element.decompose()

            text = soup.get_text()
            
            # Normalize whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks_text = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks_text if chunk)
            return clean_text if clean_text else None

        except Exception as e:
            logger.warning(f"Error fetching URL {url}: {e}")
            return None
