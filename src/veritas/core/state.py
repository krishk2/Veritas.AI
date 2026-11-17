from typing import List, Dict, Optional, TypedDict, Any

class AgentState(TypedDict, total=False):
    """
    Represents the state of the misinformation verification pipeline.
    """
    claim: str
    canonical_claim: Optional[str]
    is_duplicate: Optional[bool]
    is_duplicate_of: Optional[str]
    duplicate_match: Optional[Dict[str, Any]]
    image_base64: Optional[str]
    image_url: Optional[str]
    video_base64: Optional[str]
    video_url: Optional[str]
    image_metadata: Optional[Dict[str, Any]]
    image_forensics: Optional[Dict[str, Any]]
    video_forensics: Optional[Dict[str, Any]]
    visual_evidence: Optional[List[Dict[str, Any]]]
    sources: List[Dict[str, Any]]
    chunks: List[str]
    retrieved_passages: List[str]
    evidence: List[Dict[str, Any]]
    verdict: str
    confidence: float
    explanation: str
    adjusted_confidence: float
    credibility_report: List[Dict[str, Any]]
    record_id: str
    status: str
