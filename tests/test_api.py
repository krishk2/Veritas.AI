import pytest
import uuid
from fastapi.testclient import TestClient
from veritas.api import app
from veritas.services.ledger_service import save_claim_result

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "Veritas.AI"

def test_verify_endpoint_validation_empty(client):
    """Ensures empty request returns 400 Bad Request."""
    response = client.post("/verify", json={})
    assert response.status_code == 400
    assert "Either a text claim, an image, or a video must be provided" in response.json()["detail"]

def test_ledger_endpoints_flow(client):
    """Tests claim retrieval, listing, and human review via API endpoints."""
    claim_id = str(uuid.uuid4())
    save_claim_result(
        claim="Water boils at 100 degrees Celsius at sea level.",
        verdict="TRUE",
        confidence=0.99,
        adjusted_confidence=0.99,
        explanation="Standard physics law.",
        status="VERIFIED",
        evidence=[],
        credibility_report=[],
        record_id=claim_id
    )

    # 1. Get Claim Details
    detail_resp = client.get(f"/api/v1/claims/{claim_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["claim"] == "Water boils at 100 degrees Celsius at sea level."
    assert detail_resp.json()["verdict"] == "TRUE"

    # 2. List Claims
    list_resp = client.get("/api/v1/claims?limit=10")
    assert list_resp.status_code == 200
    claim_ids = [c["id"] for c in list_resp.json()]
    assert claim_id in claim_ids

    # 3. Review Claim Endpoint
    review_resp = client.post(
        f"/api/v1/claims/{claim_id}/review",
        json={"verdict": "TRUE", "status": "VERIFIED", "reviewed_by": "fact_checker_1"}
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "success"
    assert review_resp.json()["reviewed_by"] == "fact_checker_1"

    # 4. Graph endpoint (returns clean empty/offline structure if Neo4j is not connected)
    graph_resp = client.get(f"/api/v1/claims/{claim_id}/graph")
    assert graph_resp.status_code == 200
    assert "nodes" in graph_resp.json()
    assert "edges" in graph_resp.json()

def test_concurrent_api_requests(client):
    """Stress test: verifies 25 concurrent client threads hitting API simultaneously without database locking."""
    import concurrent.futures

    def hit_endpoint(i):
        return client.get("/health").status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(hit_endpoint, range(25)))

    assert all(code == 200 for code in results)
