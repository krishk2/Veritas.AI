from typing import Protocol, List, Dict, Any, Optional, Tuple, Union, runtime_checkable

@runtime_checkable
class ISearchProvider(Protocol):
    """Abstraction for web search engines (Tavily, Google, DuckDuckGo, etc.)."""
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        ...

@runtime_checkable
class IContentFetcher(Protocol):
    """Abstraction for retrieving and stripping HTML content from URLs."""
    def fetch_and_clean(self, url: str) -> Optional[str]:
        ...

@runtime_checkable
class ICredibilityEvaluator(Protocol):
    """Abstraction for domain credibility scoring and confidence weighting."""
    def evaluate(
        self,
        sources: List[Dict[str, Any]],
        base_confidence: float
    ) -> Tuple[float, List[Dict[str, Any]]]:
        ...

@runtime_checkable
class IImageForensicsService(Protocol):
    """Abstraction for image metadata extraction and tampering detection."""
    def analyze(self, image_input: Union[str, bytes]) -> Dict[str, Any]:
        ...

@runtime_checkable
class IVideoForensicsService(Protocol):
    """Abstraction for deepfake and synthetic AI video detection."""
    def analyze(
        self,
        video_input: Union[str, bytes],
        claim_context: Optional[str] = None,
        max_keyframes: int = 5
    ) -> Dict[str, Any]:
        ...

@runtime_checkable
class IClaimDedupService(Protocol):
    """Abstraction for semantic claim normalization and deduplication."""
    def normalize_claim(self, claim: str) -> str:
        ...

    def find_duplicate(
        self,
        canonical_claim: str,
        threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        ...

    def index_claim(
        self,
        record_id: str,
        canonical_claim: str,
        verdict: str,
        confidence: float,
        explanation: str,
        persist: bool = True
    ) -> None:
        ...

    def hydrate(self, claims: List[Dict[str, Any]]) -> int:
        ...

@runtime_checkable
class IReverseImageProvider(Protocol):
    """Abstraction for reverse image lookup and web recycling detection."""
    def search(
        self,
        image_input: Optional[Union[str, bytes]] = None,
        image_url: Optional[str] = None,
        claim: Optional[str] = None
    ) -> Dict[str, Any]:
        ...

@runtime_checkable
class ILedgerRepository(Protocol):
    """Abstraction for Dynamic Truth Ledger persistence (SQLite, Postgres, etc.)."""
    def save_claim(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        adjusted_confidence: float,
        explanation: str,
        status: str,
        evidence: List[Dict[str, Any]],
        credibility_report: List[Dict[str, Any]],
        has_image: bool = False,
        record_id: Optional[str] = None,
        canonical_claim: Optional[str] = None,
        is_duplicate_of: Optional[str] = None
    ) -> Any:
        ...

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        ...

    def list_claims(self, limit: int = 20, status: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def list_all_verified_claims(self) -> List[Dict[str, Any]]:
        ...

    def update_review(
        self,
        claim_id: str,
        verdict: Optional[str] = None,
        status: str = "VERIFIED",
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> Optional[Any]:
        ...

@runtime_checkable
class IGraphRepository(Protocol):
    """Abstraction for Trace-the-Source knowledge graph persistence (Neo4j, NetworkX, etc.)."""
    def record_provenance(
        self,
        claim_id: str,
        claim: str,
        verdict: str,
        confidence: float,
        status: str,
        sources: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        credibility_report: List[Dict[str, Any]]
    ) -> bool:
        ...

    def get_subgraph(self, claim_id: str) -> Dict[str, Any]:
        ...

    def is_available(self) -> bool:
        ...
