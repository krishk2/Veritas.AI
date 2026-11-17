import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from langgraph.graph import StateGraph, END

from veritas.core.state import AgentState
from veritas.agents.dedup_agent import dedup_agent
from veritas.agents.source_agent import source_agent
from veritas.agents.fetch_agent import fetch_agent
from veritas.agents.retriever_agent import retriever_agent
from veritas.agents.reputation_agent import reputation_agent
from veritas.agents.image_agent import image_agent
from veritas.agents.reverse_image_agent import reverse_image_agent
from veritas.agents.video_agent import video_agent
from veritas.agents.evidence_agent import evidence_agent
from veritas.agents.judge_agent import judge_agent
from veritas.agents.ledger_agent import ledger_agent

def check_duplicate_route(state: AgentState) -> str:
    """
    Evaluates whether the incoming claim is an indexed duplicate.
    If matched in the Truth Ledger (exact or semantic similarity >= 0.85),
    short-circuits directly to ledger_agent in < 5ms.
    Otherwise, proceeds to parallel multimodal investigation.
    """
    if state.get("is_duplicate"):
        print(f"[ROUTER] Cache hit (Confidence: {state.get('confidence')}). Short-circuiting directly to ledger_agent.")
        return "ledger_agent"

    return "parallel_investigation_agent"

def parallel_investigation_agent(state: AgentState) -> Dict[str, Any]:
    """
    High-Performance Barrier Synchronization Coordinator:
    Fans out the 4 investigative tracks across concurrent threads:
      - Track A: Web Text Retrieval (Source Search -> HTML Fetch -> FAISS Vector Retriever)
      - Track B: Domain Credibility Audit (Reputation scoring of web sources)
      - Track C: Multimodal Image Forensics (ELA + Vision + Reverse Image Lookup)
      - Track D: Video Forensics (Keyframe Deepfake & Temporal Inconsistency Analysis)
    Waits for all 4 tracks to complete before passing unified state to EvidenceAgent.
    """
    print("---Parallel Multi-Track Fan-Out Started---")
    start_time = time.time()
    merged_updates: Dict[str, Any] = {}

    def run_track_a() -> Dict[str, Any]:
        """Track A: Source Search -> Web Fetch -> Vector Retriever"""
        updates: Dict[str, Any] = {}
        s1 = source_agent({**state, **updates})
        updates.update(s1)
        s2 = fetch_agent({**state, **updates})
        updates.update(s2)
        s3 = retriever_agent({**state, **updates})
        updates.update(s3)
        return updates

    def run_track_b() -> Dict[str, Any]:
        """Track B: Domain Reputation Audit (parallel to text fetch/embedding)"""
        # Needs sources from source_agent or initial state
        # Run source search first if not present
        temp_state = dict(state)
        if not temp_state.get("sources"):
            s1 = source_agent(temp_state)
            temp_state.update(s1)
        return reputation_agent(temp_state)

    def run_track_c() -> Dict[str, Any]:
        """Track C: Image Forensics -> Reverse Image Search"""
        updates: Dict[str, Any] = {}
        s1 = image_agent({**state, **updates})
        updates.update(s1)
        s2 = reverse_image_agent({**state, **updates})
        updates.update(s2)
        return updates

    def run_track_d() -> Dict[str, Any]:
        """Track D: Video Deepfake Forensics"""
        return video_agent(state)

    # Execute all 4 tracks concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_a = executor.submit(run_track_a)
        future_b = executor.submit(run_track_b)
        future_c = executor.submit(run_track_c)
        future_d = executor.submit(run_track_d)

        # Collect results
        for future in as_completed([future_a, future_b, future_c, future_d]):
            try:
                track_result = future.result()
                if track_result:
                    merged_updates.update(track_result)
            except Exception as e:
                print(f"[Parallel Fan-Out Error] Worker thread failed: {e}")

    elapsed = round((time.time() - start_time) * 1000, 1)
    print(f"---Parallel Multi-Track Barrier Synchronization Completed in {elapsed}ms---")
    return merged_updates

def create_graph():
    """
    Constructs the LangGraph DAG with verified barrier synchronization,
    concurrent multimodal execution, and sub-second cache short-circuiting.
    """
    workflow = StateGraph(AgentState)

    # Core Nodes
    workflow.add_node("dedup_agent", dedup_agent)
    workflow.add_node("parallel_investigation_agent", parallel_investigation_agent)
    workflow.add_node("evidence_agent", evidence_agent)
    workflow.add_node("judge_agent", judge_agent)
    workflow.add_node("ledger_agent", ledger_agent)

    # 1. Pipeline Entry: Ingestion & Cache Check
    workflow.set_entry_point("dedup_agent")

    # 2. Fast Cache Router: If duplicate, bypass directly to ledger_agent in < 5ms
    workflow.add_conditional_edges(
        "dedup_agent",
        check_duplicate_route,
        {
            "ledger_agent": "ledger_agent",
            "parallel_investigation_agent": "parallel_investigation_agent",
        }
    )

    # 3. Synchronized Fan-In: Evidence Agent fuses all signals
    workflow.add_edge("parallel_investigation_agent", "evidence_agent")

    # 4. Decision & Synthesis: Judge Agent evaluates fused evidence
    workflow.add_edge("evidence_agent", "judge_agent")

    # 5. Dual Persistence: Relational Ledger + Neo4j Graph
    workflow.add_edge("judge_agent", "ledger_agent")
    workflow.add_edge("ledger_agent", END)

    app = workflow.compile()
    return app
