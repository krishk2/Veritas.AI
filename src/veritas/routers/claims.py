from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from veritas.schemas.claim import ReviewRequest
from veritas.core.interfaces import ILedgerRepository
from veritas.core.container import container

router = APIRouter(prefix="/api/v1/claims", tags=["Dynamic Truth Ledger"])

@router.get("", response_model=List[Dict[str, Any]])
def get_recent_claims(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status (e.g. PENDING_HUMAN_REVIEW, VERIFIED)"),
    ledger_repo: ILedgerRepository = Depends(container.get_ledger_repository)
):
    """
    Lists verified and pending claims recorded in the Dynamic Truth Ledger.
    """
    return ledger_repo.list_claims(limit=limit, status=status)

@router.get("/{claim_id}")
def get_claim_details(
    claim_id: str,
    ledger_repo: ILedgerRepository = Depends(container.get_ledger_repository)
):
    """
    Retrieves full claim details, evidence citations, and credibility audits by ID.
    """
    claim = ledger_repo.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found in ledger.")
    return claim

@router.post("/{claim_id}/review")
def review_claim(
    claim_id: str,
    review: ReviewRequest,
    ledger_repo: ILedgerRepository = Depends(container.get_ledger_repository)
):
    """
    Human-in-the-Loop review endpoint to confirm, modify, or override verdicts on flagged claims.
    """
    updated = ledger_repo.update_review(
        claim_id=claim_id,
        verdict=review.verdict,
        status=review.status,
        reviewed_by=review.reviewed_by,
        review_notes=review.review_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Claim not found in ledger.")
    return {
        "status": "success",
        "claim_id": updated.id,
        "verdict": updated.verdict,
        "review_status": updated.status,
        "reviewed_by": updated.reviewed_by
    }
