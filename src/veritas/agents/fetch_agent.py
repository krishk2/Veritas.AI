from typing import Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from veritas.core.state import AgentState
from veritas.core.container import container

def fetch_agent(state: AgentState) -> Dict[str, Any]:
    """
    FetchAgent: Fetches content using IContentFetcher and splits text into chunks.
    """
    print("---FetchAgent---")
    sources = state.get("sources", [])
    
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    fetcher = container.get_content_fetcher()
    
    for source in sources:
        # Use high-quality pre-extracted content from search engine directly (sub-millisecond)
        clean_text = source.get("content") or source.get("snippet")
        
        # Fallback to direct HTTP fetch only if search snippet is unavailable
        if not clean_text and source.get("url"):
            try:
                clean_text = fetcher.fetch_and_clean(source["url"])
            except Exception:
                clean_text = None

        if not clean_text:
            continue
            
        source_chunks = text_splitter.split_text(clean_text)
        chunks.extend(source_chunks[:3])
        
    return {"chunks": chunks}
