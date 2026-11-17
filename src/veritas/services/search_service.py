import os
import logging
from typing import List, Dict, Any, Optional
from veritas.core.interfaces import ISearchProvider

logger = logging.getLogger("veritas.search_service")

class TavilySearchProvider:
    """Production implementation of ISearchProvider using Tavily."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("TAVILY_API_KEY is not configured.")
            return []

        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tool = TavilySearchResults(max_results=max_results)
            results = tool.invoke({"query": query})
            
            sources = []
            for res in results:
                content_text = res.get("content", "")
                sources.append({
                    "url": res.get("url", ""),
                    "title": res.get("title", "No Title"),
                    "content": content_text,
                    "snippet": content_text,
                    "date": ""
                })
            return sources
        except Exception as e:
            logger.error(f"Tavily search execution failed: {e}")
            return []

class DuckDuckGoSearchProvider(ISearchProvider):
    """Zero-key, ultra-fast web intelligence using DuckDuckGo."""

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            results = list(DDGS().text(query, max_results=max_results))
            sources = []
            for r in results:
                body = r.get("body", "")
                sources.append({
                    "url": r.get("href", ""),
                    "title": r.get("title", "DuckDuckGo Result"),
                    "content": body,
                    "snippet": body,
                    "date": ""
                })
            return sources
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

class HybridSearchProvider(ISearchProvider):
    """
    Intelligent Search Provider:
    Checks SEARCH_PROVIDER env var ('tavily', 'duckduckgo', or 'auto').
    If Tavily is unavailable or missing API key, seamlessly falls back to DuckDuckGo (0.6s latency).
    """

    def __init__(
        self,
        tavily_provider: Optional[ISearchProvider] = None,
        ddg_provider: Optional[ISearchProvider] = None
    ):
        self.tavily = tavily_provider or TavilySearchProvider()
        self.ddg = ddg_provider or DuckDuckGoSearchProvider()
        self.preferred = os.getenv("SEARCH_PROVIDER", "auto").lower()

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if self.preferred == "duckduckgo":
            logger.info("Using DuckDuckGo search provider as explicitly configured.")
            return self.ddg.search(query, max_results=max_results)

        # Try Tavily if configured
        if os.getenv("TAVILY_API_KEY"):
            results = self.tavily.search(query, max_results=max_results)
            if results:
                return results
            logger.info("Tavily search returned 0 results or failed; falling back to DuckDuckGo.")

        # Seamless DuckDuckGo fallback
        return self.ddg.search(query, max_results=max_results)

class MockSearchProvider:
    """Mock search provider for testing and offline environments."""
    
    def __init__(self, preset_results: Optional[List[Dict[str, Any]]] = None):
        self.preset_results = preset_results or [
            {"url": "https://www.bbc.com/news/test-1", "title": "BBC News", "snippet": "Sample verified news snippet."},
            {"url": "https://www.reuters.com/article/test-2", "title": "Reuters Fact Check", "snippet": "Reuters evidence snippet."}
        ]

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return self.preset_results[:max_results]
