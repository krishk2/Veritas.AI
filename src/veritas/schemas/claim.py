from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class VerifyRequest(BaseModel):
    claim: Optional[str] = None
    url: Optional[str] = None
    image_base64: Optional[str] = None
    video_base64: Optional[str] = None

class SourceCitation(BaseModel):
    citation_id: int
    title: str
    url: str
    domain: str
    favicon_url: Optional[str] = None
    credibility_status: str = "Neutral"  # Trusted, Questionable, Neutral
    credibility_score: float = 0.5
    snippet: Optional[str] = None

class AgentExecutionStep(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    tools: List[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    duration_ms: int
    status: str = "completed"

class VerifyResponse(BaseModel):
    record_id: Optional[str] = None
    status: str = "VERIFIED"  # VERIFIED or PENDING_HUMAN_REVIEW
    verdict: str
    confidence: float
    explanation: str
    evidence: List[Dict[str, Any]]
    credibility_report: List[Dict[str, Any]]
    sources: List[SourceCitation] = []
    has_image: bool = False
    has_video: bool = False
    canonical_claim: Optional[str] = None
    is_duplicate: bool = False
    image_forensics: Optional[Dict[str, Any]] = None
    image_metadata: Optional[Dict[str, Any]] = None
    video_forensics: Optional[Dict[str, Any]] = None
    execution_trace: List[AgentExecutionStep] = []
    neo4j_connected: bool = False
    provenance_graph: Optional[Dict[str, Any]] = None

class ReviewRequest(BaseModel):
    verdict: Optional[str] = None  # e.g., "TRUE", "FALSE", "MIXTURE"
    status: str = "VERIFIED"
    reviewed_by: str = "editorial_team"
    review_notes: Optional[str] = None
