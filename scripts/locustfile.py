"""
Veritas.AI High-Concurrency Load Testing Suite (Locust)
Simulates 100+ concurrent users querying the verification engine:
- Recurring viral claims (benchmarks Phase 3 deduplication cache hit latency)
- New distinct claims (benchmarks multi-agent pipeline under load)
- Health checks and Truth Ledger queries

Usage:
  uv add locust
  uv run locust -f scripts/locustfile.py --host=http://localhost:8001
"""

from locust import HttpUser, task, between
import random

SAMPLE_CLAIMS = [
    "Drinking lemon water cures cancer",
    "The Great Wall of China is visible from the Moon with naked eyes",
    "NASA found extraterrestrial bacterial life on Mars",
    "Electric vehicles produce zero lifetime carbon emissions",
    "5G cellular towers transmit respiratory viruses",
    "Vaccines contain tracking microchips",
    "Antarctica is completely melting into the ocean",
    "Humans only use 10 percent of their brain capacity"
]

class VeritasUser(HttpUser):
    # Simulate realistic human reading time between actions (1 to 3 seconds)
    wait_time = between(1.0, 3.0)

    @task(5)
    def verify_viral_duplicate_claim(self):
        """Simulates traffic spikes on viral rumors (tests sub-50ms cache short-circuit)."""
        payload = {
            "claim": "Is it true that drinking hot lemon water cures cancer???"
        }
        self.client.post("/verify", json=payload, name="/verify [Duplicate Cache Hit]")

    @task(2)
    def verify_random_claim(self):
        """Simulates diverse users verifying different web claims."""
        claim = random.choice(SAMPLE_CLAIMS)
        payload = {"claim": claim}
        self.client.post("/verify", json=payload, name="/verify [Distinct Claim]")

    @task(3)
    def check_health(self):
        """Lightweight heartbeat check."""
        self.client.get("/health", name="/health")

    @task(1)
    def list_truth_ledger(self):
        """Simulates users viewing the Truth Ledger dashboard."""
        self.client.get("/claims?limit=10", name="/claims [List Ledger]")
