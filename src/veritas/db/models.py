from typing import Optional, List
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field, Relationship

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ClaimRecord(SQLModel, table=True):
    __tablename__ = "claim_records"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    claim_text: str = Field(index=True)
    canonical_claim: Optional[str] = Field(default=None, index=True)
    is_duplicate_of: Optional[str] = Field(default=None, index=True)
    verdict: str = Field(index=True)  # TRUE, FALSE, UNCLEAR
    confidence: float = Field(default=0.0)
    adjusted_confidence: float = Field(default=0.0)
    explanation: str
    status: str = Field(default="VERIFIED", index=True)  # VERIFIED, PENDING_HUMAN_REVIEW
    has_image: bool = Field(default=False)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    reviewed_by: Optional[str] = Field(default=None)
    review_notes: Optional[str] = Field(default=None)

    # Relationships
    evidence_items: List["EvidenceRecord"] = Relationship(back_populates="claim_record")
    credibility_audits: List["CredibilityAuditRecord"] = Relationship(back_populates="claim_record")

class EvidenceRecord(SQLModel, table=True):
    __tablename__ = "evidence_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim_records.id", index=True)
    sentence: str
    label: str  # SUPPORT, REFUTE
    score: float
    source_url: Optional[str] = None

    claim_record: Optional[ClaimRecord] = Relationship(back_populates="evidence_items")

class CredibilityAuditRecord(SQLModel, table=True):
    __tablename__ = "credibility_audit_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: str = Field(foreign_key="claim_records.id", index=True)
    domain: str
    url: Optional[str] = None
    status: str  # Trusted, Questionable, Neutral

    claim_record: Optional[ClaimRecord] = Relationship(back_populates="credibility_audits")
