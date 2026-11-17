import pytest
from veritas.schemas.claim import SourceCitation, VerifyResponse
from veritas.agents.judge_agent import judge_agent

def test_source_citation_schema():
    citation = SourceCitation(
        citation_id=1,
        title="Reuters Fact Check",
        url="https://www.reuters.com/fact-check/example-story",
        domain="reuters.com",
        favicon_url="https://www.google.com/s2/favicons?domain=reuters.com&sz=64",
        credibility_status="Trusted",
        credibility_score=0.95,
        snippet="Official statements confirm the claim is unfounded."
    )
    
    assert citation.citation_id == 1
    assert citation.domain == "reuters.com"
    assert citation.credibility_status == "Trusted"
    assert "reuters.com" in citation.favicon_url

def test_verify_response_includes_sources_strip():
    citations = [
        SourceCitation(
            citation_id=1,
            title="AP News",
            url="https://apnews.com/article/123",
            domain="apnews.com",
            credibility_status="Trusted"
        ),
        SourceCitation(
            citation_id=2,
            title="NASA Official Release",
            url="https://nasa.gov/news/mars",
            domain="nasa.gov",
            credibility_status="Trusted"
        )
    ]
    
    response = VerifyResponse(
        verdict="FALSE",
        confidence=0.92,
        explanation="NASA confirmed that no extraterrestrial organisms were identified [1], corroborating AP reports [2].",
        evidence=[],
        credibility_report=[],
        sources=citations
    )
    
    assert len(response.sources) == 2
    assert response.sources[0].citation_id == 1
    assert response.sources[1].domain == "nasa.gov"
    assert "[1]" in response.explanation
    assert "[2]" in response.explanation

def test_judge_agent_fallback_preserves_citations():
    state = {
        "claim": "Fake moon landing claim",
        "evidence": [],
        "sources": [
            {
                "title": "NASA Archives",
                "url": "https://history.nasa.gov/apollo.html",
                "content": "Full mission logs of Apollo 11."
            }
        ],
        "image_forensics": {
            "has_image": True,
            "is_tampered_or_ai": True,
            "summary": "AI generation signature detected."
        }
    }
    
    result = judge_agent(state)
    assert result["verdict"] == "FALSE"
    assert "[1]" in result["explanation"]
