from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from veritas.db.session import engine, init_db
from veritas.db.models import ClaimRecord, EvidenceRecord, CredibilityAuditRecord, get_utc_now
from veritas.core.interfaces import ILedgerRepository

class RelationalLedgerRepository(ILedgerRepository):
    """SQLModel/SQLAlchemy implementation of the Dynamic Truth Ledger repository."""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

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
    ) -> ClaimRecord:
        init_db()
        with Session(self.engine) as session:
            record = ClaimRecord(
                id=record_id or ClaimRecord.__fields__["id"].default_factory(),
                claim_text=claim,
                canonical_claim=canonical_claim,
                is_duplicate_of=is_duplicate_of,
                verdict=verdict,
                confidence=confidence,
                adjusted_confidence=adjusted_confidence,
                explanation=explanation,
                status=status,
                has_image=has_image,
                created_at=get_utc_now(),
                updated_at=get_utc_now()
            )
            session.add(record)
            session.flush()

            for item in (evidence or []):
                ev = EvidenceRecord(
                    claim_id=record.id,
                    sentence=item.get("sentence", ""),
                    label=item.get("label", "NEUTRAL"),
                    score=float(item.get("score", 0.0)),
                    source_url=item.get("source_url")
                )
                session.add(ev)

            for cred in (credibility_report or []):
                cr = CredibilityAuditRecord(
                    claim_id=record.id,
                    domain=cred.get("domain", "unknown"),
                    url=cred.get("url"),
                    status=cred.get("status", "Neutral")
                )
                session.add(cr)

            session.commit()
            session.refresh(record)
            return record

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        init_db()
        with Session(self.engine) as session:
            statement = select(ClaimRecord).where(ClaimRecord.id == claim_id)
            claim = session.exec(statement).first()
            if not claim:
                return None
                
            evidence = session.exec(select(EvidenceRecord).where(EvidenceRecord.claim_id == claim_id)).all()
            credibility = session.exec(select(CredibilityAuditRecord).where(CredibilityAuditRecord.claim_id == claim_id)).all()
            
            return {
                "id": claim.id,
                "claim": claim.claim_text,
                "verdict": claim.verdict,
                "confidence": claim.confidence,
                "adjusted_confidence": claim.adjusted_confidence,
                "explanation": claim.explanation,
                "status": claim.status,
                "has_image": claim.has_image,
                "created_at": claim.created_at.isoformat() if claim.created_at else None,
                "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
                "reviewed_by": claim.reviewed_by,
                "review_notes": claim.review_notes,
                "evidence": [
                    {"sentence": e.sentence, "label": e.label, "score": e.score, "source_url": e.source_url}
                    for e in evidence
                ],
                "credibility_report": [
                    {"domain": c.domain, "url": c.url, "status": c.status}
                    for c in credibility
                ]
            }

    def list_claims(self, limit: int = 20, status: Optional[str] = None) -> List[Dict[str, Any]]:
        init_db()
        with Session(self.engine) as session:
            statement = select(ClaimRecord).order_by(ClaimRecord.created_at.desc()).limit(limit)
            if status:
                statement = statement.where(ClaimRecord.status == status)
            records = session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "claim": r.claim_text,
                    "verdict": r.verdict,
                    "adjusted_confidence": r.adjusted_confidence,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in records
            ]

    def list_all_verified_claims(self) -> List[Dict[str, Any]]:
        """Retrieves all historical verified claims for vector index cold-start hydration."""
        init_db()
        with Session(self.engine) as session:
            statement = select(ClaimRecord).where(ClaimRecord.status == "VERIFIED")
            records = session.exec(statement).all()
            return [
                {
                    "record_id": r.id,
                    "canonical_claim": r.canonical_claim or r.claim_text,
                    "verdict": r.verdict,
                    "confidence": r.adjusted_confidence or r.confidence,
                    "explanation": r.explanation
                }
                for r in records
            ]

    def update_review(
        self,
        claim_id: str,
        verdict: Optional[str] = None,
        status: str = "VERIFIED",
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> Optional[ClaimRecord]:
        init_db()
        with Session(self.engine) as session:
            statement = select(ClaimRecord).where(ClaimRecord.id == claim_id)
            claim = session.exec(statement).first()
            if not claim:
                return None
            
            if verdict:
                claim.verdict = verdict
            claim.status = status
            claim.reviewed_by = reviewed_by
            claim.review_notes = review_notes
            claim.updated_at = get_utc_now()
            
            session.add(claim)
            session.commit()
            session.refresh(claim)
            return claim

# Global default instance
_default_ledger_repo = RelationalLedgerRepository()

def get_ledger_repository() -> ILedgerRepository:
    return _default_ledger_repo

# Functional aliases for backward compatibility
def save_claim_result(*args, **kwargs) -> ClaimRecord:
    return _default_ledger_repo.save_claim(*args, **kwargs)

def get_claim_by_id(claim_id: str) -> Optional[Dict[str, Any]]:
    return _default_ledger_repo.get_claim(claim_id)

def list_claims(limit: int = 20, status: Optional[str] = None) -> List[Dict[str, Any]]:
    return _default_ledger_repo.list_claims(limit=limit, status=status)

def update_claim_review(*args, **kwargs) -> Optional[ClaimRecord]:
    return _default_ledger_repo.update_review(*args, **kwargs)
