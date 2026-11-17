from typing import Dict, Any
from veritas.core.state import AgentState
from veritas.core.container import container

def reputation_agent(state: AgentState) -> Dict[str, Any]:
    """
    ReputationAgent: Evaluates source credibility and adjusts confidence using ICredibilityEvaluator.
    """
    print("---ReputationAgent---")
    sources = state.get("sources", [])
    base_confidence = state.get("confidence", 0.5)
    
    evaluator = container.get_credibility_evaluator()
    adjusted_confidence, credibility_report = evaluator.evaluate(sources, base_confidence)
    
    print(f"Confidence adjusted from {base_confidence} to {adjusted_confidence}")
    
    return {
        "adjusted_confidence": adjusted_confidence,
        "credibility_report": credibility_report
    }
