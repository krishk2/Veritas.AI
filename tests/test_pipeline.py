import pytest
from veritas.state import AgentState
from veritas.graph import create_graph
from veritas.agents.reputation_agent import reputation_agent
from veritas.agents.ledger_agent import ledger_agent

def test_graph_initialization():
    """Verify that the LangGraph pipeline initializes and compiles with all nodes."""
    graph = create_graph()
    assert graph is not None
    # Verify node names are present in graph
    node_names = list(graph.nodes.keys())
    assert "source_agent" in node_names
    assert "fetch_agent" in node_names
    assert "retriever_agent" in node_names
    assert "evidence_agent" in node_names
    assert "judge_agent" in node_names
    assert "reputation_agent" in node_names
    assert "ledger_agent" in node_names

def test_reputation_agent_trusted_domain():
    """Verify reputation score adjustment for trusted sources."""
    mock_state: AgentState = {
        "claim": "Test claim",
        "sources": [{"url": "https://www.bbc.com/news/123"}],
        "chunks": [],
        "retrieved_passages": [],
        "evidence": [],
        "verdict": "TRUE",
        "confidence": 0.7,
        "explanation": "Test explanation",
        "adjusted_confidence": 0.0,
        "credibility_report": [],
        "record_id": ""
    }
    result = reputation_agent(mock_state)
    assert result["adjusted_confidence"] == pytest.approx(0.8, abs=0.01)
    assert result["credibility_report"][0]["status"] == "Trusted"

def test_reputation_agent_questionable_domain():
    """Verify reputation score penalty for questionable sources."""
    mock_state: AgentState = {
        "claim": "Test claim",
        "sources": [{"url": "https://clickbait.com/article/456"}],
        "chunks": [],
        "retrieved_passages": [],
        "evidence": [],
        "verdict": "TRUE",
        "confidence": 0.5,
        "explanation": "Test explanation",
        "adjusted_confidence": 0.0,
        "credibility_report": [],
        "record_id": ""
    }
    result = reputation_agent(mock_state)
    assert result["adjusted_confidence"] == pytest.approx(0.3, abs=0.01)
    assert result["credibility_report"][0]["status"] == "Questionable"

def test_ledger_agent_serialization():
    """Verify ledger agent generates valid record with id."""
    mock_state: AgentState = {
        "claim": "Test claim",
        "sources": [],
        "chunks": [],
        "retrieved_passages": [],
        "evidence": [],
        "verdict": "FALSE",
        "confidence": 0.9,
        "explanation": "Debunked claim",
        "adjusted_confidence": 0.9,
        "credibility_report": [],
        "record_id": ""
    }
    result = ledger_agent(mock_state)
    assert "record_id" in result
    assert len(result["record_id"]) > 0
