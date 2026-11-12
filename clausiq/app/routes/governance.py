from fastapi import APIRouter, Depends, HTTPException

from ..agents.gate import decide_approval, list_approvals, run_red_team
from ..audit import get_entries
from ..db import query_one
from ..models import ApprovalDecision
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["governance"])


@router.get("/approvals")
def approvals(status: str | None = None, contract_id: int | None = None,
              user: dict = Depends(get_current_user)):
    return list_approvals(status=status, contract_id=contract_id)


@router.post("/approvals/{approval_id}/decision")
def approval_decision(
    approval_id: int, payload: ApprovalDecision, user: dict = Depends(get_current_user)
):
    result = decide_approval(approval_id, payload.decision, payload.note, user)
    if not result:
        raise HTTPException(status_code=404, detail="Approval not found")
    return query_one("SELECT * FROM approvals WHERE id = ?", (approval_id,))


@router.get("/audit")
def audit_log(contract_id: int | None = None, limit: int = 200, offset: int = 0,
              user: dict = Depends(get_current_user)):
    return get_entries(contract_id=contract_id, limit=min(limit, 500), offset=offset)


@router.post("/redteam")
def red_team(user: dict = Depends(get_current_user)):
    return run_red_team(user["name"])
