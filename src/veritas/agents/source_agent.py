from typing import Dict, Any
from veritas.core.state import AgentState
from veritas.core.container import container

def source_agent(state: AgentState) -> Dict[str, Any]:
    """
    SourceAgent: Discovers relevant URLs using the configured ISearchProvider abstraction.
    """
    print("---SourceAgent---")
    claim = state.get("canonical_claim") or state["claim"]
    print(f"Searching for: {claim}")
    
    search_provider = container.get_search_provider()
    sources = search_provider.search(claim, max_results=5)
    
    return {"sources": sources}
