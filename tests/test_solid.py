import pytest
from veritas.core.interfaces import (
    ISearchProvider,
    IContentFetcher,
    ICredibilityEvaluator,
    ILedgerRepository,
    IGraphRepository
)
from veritas.core.container import container, DependencyContainer
from veritas.services.search_service import MockSearchProvider, TavilySearchProvider
from veritas.services.fetcher_service import HtmlContentFetcher
from veritas.services.credibility_service import RuleBasedCredibilityEvaluator
from veritas.services.ledger_service import RelationalLedgerRepository
from veritas.services.neo4j_service import Neo4jGraphRepository
from veritas.agents.source_agent import source_agent
from veritas.agents.reputation_agent import reputation_agent
from veritas.state import AgentState

def test_interface_compliance():
    """Verify that all concrete services adhere to their respective abstract protocols (LSP / ISP)."""
    assert isinstance(MockSearchProvider(), ISearchProvider)
    assert isinstance(TavilySearchProvider(), ISearchProvider)
    assert isinstance(HtmlContentFetcher(), IContentFetcher)
    assert isinstance(RuleBasedCredibilityEvaluator(), ICredibilityEvaluator)
    assert isinstance(RelationalLedgerRepository(), ILedgerRepository)
    assert isinstance(Neo4jGraphRepository(), IGraphRepository)

def test_dependency_inversion_search_provider():
    """Demonstrates Dependency Inversion (DIP) and Open/Closed (OCP) by injecting a mock search engine."""
    custom_results = [
        {"url": "https://custom-factchecker.org/article-1", "title": "Custom Title", "snippet": "Custom snippet."}
    ]
    mock_provider = MockSearchProvider(preset_results=custom_results)
    
    # Save original provider and inject mock
    original_provider = container.get_search_provider()
    container.set_search_provider(mock_provider)
    
    try:
        mock_state: AgentState = {"claim": "Test claim"}
        result = source_agent(mock_state)
        assert len(result["sources"]) == 1
        assert result["sources"][0]["url"] == "https://custom-factchecker.org/article-1"
    finally:
        container.set_search_provider(original_provider)

def test_open_closed_credibility_evaluator():
    """Demonstrates Open/Closed (OCP) by extending credibility rules without modifying agent code."""
    custom_evaluator = RuleBasedCredibilityEvaluator(
        trusted_domains=["custom-trusted-domain.com"],
        questionable_domains=["custom-bad-actor.net"],
        trusted_bonus=0.25,
        questionable_penalty=0.50
    )
    
    original_evaluator = container.get_credibility_evaluator()
    container.set_credibility_evaluator(custom_evaluator)
    
    try:
        mock_state: AgentState = {
            "claim": "Test claim",
            "confidence": 0.5,
            "sources": [{"url": "https://custom-trusted-domain.com/evidence"}]
        }
        result = reputation_agent(mock_state)
        # 0.5 + 0.25 = 0.75
        assert result["adjusted_confidence"] == pytest.approx(0.75, abs=0.01)
        assert result["credibility_report"][0]["status"] == "Trusted"
    finally:
        container.set_credibility_evaluator(original_evaluator)
