import os
import tempfile
import threading
import pytest
from veritas.services.dedup_service import SemanticClaimDedupService
from veritas.agents.dedup_agent import dedup_agent
from veritas.core.graph import check_duplicate_route, create_graph
from veritas.core.container import container

def test_claim_normalization_clickbait_and_framing():
    service = SemanticClaimDedupService(use_remote_embeddings=False)
    
    noisy_inputs = [
        ("Is it true that NASA found life on Mars???", "NASA found life on Mars"),
        ("BREAKING NEWS: Earthquake strikes California #breaking #news", "Earthquake strikes California"),
        ("Can you please verify if drinking bleach cures covid?!?!", "drinking bleach cures covid"),
        ("ALERT: New law bans gasoline cars immediately!", "New law bans gasoline cars immediately"),
        ("Did you hear that the moon landing was staged in a studio?", "the moon landing was staged in a studio"),
    ]
    
    for raw, expected in noisy_inputs:
        normalized = service.normalize_claim(raw)
        assert normalized == expected

def test_semantic_deduplication_exact_and_near_match():
    service = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=None)
    
    # 1. Index a claim
    service.index_claim(
        record_id="claim-101",
        canonical_claim="Drinking hot lemon water cures cancer",
        verdict="FALSE",
        confidence=0.92,
        explanation="No peer-reviewed clinical trials support lemon water curing cancer."
    )
    
    # 2. Query with exact normalized string
    exact_match = service.find_duplicate("Drinking hot lemon water cures cancer")
    assert exact_match is not None
    assert exact_match["record_id"] == "claim-101"
    assert exact_match["verdict"] == "FALSE"
    assert exact_match["similarity"] >= 0.99
    
    # 3. Query with a completely different claim
    unrelated_match = service.find_duplicate("Electric vehicles emit zero tailpipe emissions")
    assert unrelated_match is None

def test_dedup_persistence_and_reload():
    temp_dir = tempfile.mkdtemp()
    index_file = os.path.join(temp_dir, "test_index.json")
    
    # 1. Create service and save claim
    service1 = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=index_file)
    service1.index_claim(
        record_id="claim-persisted-1",
        canonical_claim="Humans only use 10 percent of their brain",
        verdict="FALSE",
        confidence=0.95,
        explanation="Neuroimaging shows almost all areas of the brain are active."
    )
    
    assert os.path.exists(index_file)
    
    # 2. Spin up a new service pointing to the same file (simulating server reboot)
    service2 = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=index_file)
    match = service2.find_duplicate("Humans only use 10 percent of their brain")
    assert match is not None
    assert match["record_id"] == "claim-persisted-1"
    assert match["verdict"] == "FALSE"
    
    # Cleanup
    try:
        os.remove(index_file)
        os.rmdir(temp_dir)
    except Exception:
        pass

def test_dedup_cold_start_hydration():
    service = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=None)
    claims_to_hydrate = [
        {
            "record_id": "topic-1",
            "canonical_claim": "Drinking coffee causes permanent chronic dehydration",
            "verdict": "FALSE",
            "confidence": 0.90,
            "explanation": "Moderate coffee consumption contributes to daily fluid intake."
        },
        {
            "record_id": "topic-2",
            "canonical_claim": "The Great Wall of China is visible from the Moon with naked eyes",
            "verdict": "FALSE",
            "confidence": 0.95,
            "explanation": "Astronauts confirm the Great Wall is not visible from lunar distance."
        },
        {
            "record_id": "topic-3",
            "canonical_claim": "Regular aerobic exercise improves cardiovascular endurance and heart health",
            "verdict": "TRUE",
            "confidence": 0.98,
            "explanation": "Extensive medical literature confirms aerobic training benefits."
        }
    ]
    
    hydrated_count = service.hydrate(claims_to_hydrate)
    assert hydrated_count == 3
    
    match = service.find_duplicate("The Great Wall of China is visible from the Moon with naked eyes")
    assert match is not None
    assert match["record_id"] == "topic-2"
    assert match["verdict"] == "FALSE"

def test_dedup_agent_new_claim():
    service = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=None)
    container.set_claim_dedup_service(service)
    
    state = {
        "claim": "Is it true that Antarctica is completely melting???"
    }
    result = dedup_agent(state)
    assert result["canonical_claim"] == "Antarctica is completely melting"
    assert result["is_duplicate"] is False
    assert result["duplicate_match"] is None

def test_dedup_agent_cache_hit_high_confidence():
    service = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=None)
    service.index_claim(
        record_id="claim-555",
        canonical_claim="The Eiffel Tower was moved to Tokyo",
        verdict="FALSE",
        confidence=0.98,
        explanation="The Eiffel Tower remains in Paris, France."
    )
    container.set_claim_dedup_service(service)
    
    state = {
        "claim": "BREAKING: The Eiffel Tower was moved to Tokyo!"
    }
    result = dedup_agent(state)
    assert result["is_duplicate"] is True
    assert result["duplicate_match"] is not None
    assert result["duplicate_match"]["record_id"] == "claim-555"
    assert result["verdict"] == "FALSE"
    assert result["confidence"] == 0.98
    assert "[Duplicate of Claim claim-555]" in result["explanation"]
    assert result["is_duplicate_of"] == "claim-555"

def test_production_graph_short_circuit_routing():
    # Cache hit with high confidence should route straight to ledger_agent
    hit_state = {
        "is_duplicate": True,
        "confidence": 0.95,
        "verdict": "FALSE"
    }
    assert check_duplicate_route(hit_state) == "ledger_agent"
    
    # Low confidence duplicate (< 0.65) should NOT short-circuit
    low_conf_state = {
        "is_duplicate": True,
        "confidence": 0.55,
        "verdict": "UNCLEAR"
    }
    assert check_duplicate_route(low_conf_state) == "source_agent"
    
    # Fresh new claim should proceed through full pipeline
    new_state = {
        "is_duplicate": False
    }
    assert check_duplicate_route(new_state) == "source_agent"

def test_thread_safe_concurrent_access():
    service = SemanticClaimDedupService(use_remote_embeddings=False, index_file_path=None)
    
    def worker(worker_id):
        for i in range(10):
            service.index_claim(
                record_id=f"thread-{worker_id}-{i}",
                canonical_claim=f"Unique proposition from thread {worker_id} item {i}",
                verdict="TRUE",
                confidence=0.88,
                explanation="Thread safe test",
                persist=False
            )
            service.find_duplicate(f"Unique proposition from thread {worker_id} item {i}")
            
    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(service._index) == 50
