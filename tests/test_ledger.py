import pytest
import os
import uuid
from veritas.db import init_db
from veritas.services.ledger_service import (
    save_claim_result,
    get_claim_by_id,
    list_claims,
    update_claim_review
)
from veritas.agents.ledger_agent import ledger_agent
from veritas.state import AgentState

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_save_and_retrieve_claim():
    claim_id = str(uuid.uuid4())
    record = save_claim_result(
        claim="Drinking green tea extends life expectancy.",
        verdict="TRUE",
        confidence=0.88,
        adjusted_confidence=0.92,
        explanation="Multiple longitudinal studies show cardiovascular benefits.",
        status="VERIFIED",
        evidence=[
            {"sentence": "Green tea polyphenols reduce all-cause mortality.", "label": "SUPPORT", "score": 0.95}
        ],
        credibility_report=[
            {"domain": "nih.gov", "url": "https://pubmed.ncbi.nlm.nih.gov/123", "status": "Trusted"}
        ],
        has_image=False,
        record_id=claim_id
    )

    assert record.id == claim_id
    assert record.status == "VERIFIED"

    # Retrieve from DB
    retrieved = get_claim_by_id(claim_id)
    assert retrieved is not None
    assert retrieved["claim"] == "Drinking green tea extends life expectancy."
    assert retrieved["verdict"] == "TRUE"
    assert len(retrieved["evidence"]) == 1
    assert retrieved["evidence"][0]["label"] == "SUPPORT"
    assert len(retrieved["credibility_report"]) == 1
    assert retrieved["credibility_report"][0]["domain"] == "nih.gov"

def test_update_claim_human_review():
    claim_id = str(uuid.uuid4())
    save_claim_result(
        claim="Ambiguous claim about aliens.",
        verdict="UNCLEAR",
        confidence=0.45,
        adjusted_confidence=0.40,
        explanation="No reliable evidence found.",
        status="PENDING_HUMAN_REVIEW",
        evidence=[],
        credibility_report=[],
        record_id=claim_id
    )

    # Apply editorial review
    updated = update_claim_review(
        claim_id=claim_id,
        verdict="FALSE",
        status="VERIFIED",
        reviewed_by="senior_editor",
        review_notes="Debunked by astronomical consensus."
    )

    assert updated is not None
    assert updated.verdict == "FALSE"
    assert updated.status == "VERIFIED"
    assert updated.reviewed_by == "senior_editor"

def test_ledger_agent_threshold_escalation():
    # Low confidence -> PENDING_HUMAN_REVIEW
    mock_state_low: AgentState = {
        "claim": "Uncertain statement",
        "verdict": "TRUE",
        "confidence": 0.40,
        "adjusted_confidence": 0.45,
        "explanation": "Weak sources",
        "evidence": [],
        "credibility_report": [],
        "sources": []
    }
    result_low = ledger_agent(mock_state_low)
    assert result_low["status"] == "PENDING_HUMAN_REVIEW"
    assert "record_id" in result_low

    # High confidence -> VERIFIED
    mock_state_high: AgentState = {
        "claim": "The Pacific Ocean is the largest ocean on Earth.",
        "verdict": "TRUE",
        "confidence": 0.95,
        "adjusted_confidence": 0.95,
        "explanation": "Geographical fact.",
        "evidence": [],
        "credibility_report": [],
        "sources": []
    }
    result_high = ledger_agent(mock_state_high)
    assert result_high["status"] == "VERIFIED"
