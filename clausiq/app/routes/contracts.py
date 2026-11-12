from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..audit import log_event
from ..config import MAX_UPLOAD_BYTES, SAMPLE_CONTRACTS_DIR
from ..db import execute, query, query_one, utcnow
from ..document import DocumentError, extract_text
from ..models import ContractCreate, ReviewRequest
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["contracts"])

SAMPLE_COUNTERPARTIES = {
    "cloudbase-vendor-agreement": "CloudBase Inc.",
    "mutual-nda": "Atlas Analytics",
    "employment-offer": "Candidate Hire",
    "event-management-agreement": "BrightStage Events",
}


def _contract_view(row: dict) -> dict:
    return dict(row)


@router.get("/contracts")
def list_contracts(user: dict = Depends(get_current_user)):
    rows = query("SELECT * FROM contracts ORDER BY id DESC")
    return [_contract_view(r) for r in rows]


@router.post("/contracts/upload")
async def upload_contract(
    user: dict = Depends(get_current_user),
    file: UploadFile = File(...),
    counterparty: str = Form("Counterparty"),
    company_playbook: str = Form("startup-friendly"),
    counterparty_playbook: str = Form("vendor-friendly"),
):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB)")
    try:
        text = extract_text(file.filename or "upload.txt", raw)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    name = Path(file.filename or "contract.txt").stem
    contract_id = execute(
        "INSERT INTO contracts (name, counterparty, filename, format, status,"
        " company_playbook, counterparty_playbook, full_text, created_at)"
        " VALUES (?, ?, ?, ?, 'uploaded', ?, ?, ?, ?)",
        (
            name,
            counterparty or "Counterparty",
            file.filename,
            Path(file.filename or "").suffix.lower(),
            company_playbook,
            counterparty_playbook,
            text,
            utcnow(),
        ),
    )
    log_event(
        user["name"], "human", "contract_uploaded",
        contract_id=contract_id,
        details={"name": name, "counterparty": counterparty, "chars": len(text)},
    )
    return query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))


@router.post("/contracts/text")
def create_from_text(
    payload: ContractCreate, user: dict = Depends(get_current_user)
):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Contract text is required")
    contract_id = execute(
        "INSERT INTO contracts (name, counterparty, filename, format, status,"
        " company_playbook, counterparty_playbook, full_text, created_at)"
        " VALUES (?, ?, NULL, 'txt', 'uploaded', ?, ?, ?, ?)",
        (
            payload.name,
            payload.counterparty,
            payload.company_playbook,
            payload.counterparty_playbook,
            text,
            utcnow(),
        ),
    )
    log_event(user["name"], "human", "contract_created",
              contract_id=contract_id, details={"name": payload.name})
    return query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: int, user: dict = Depends(get_current_user)):
    row = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    return row


@router.delete("/contracts/{contract_id}")
def delete_contract(contract_id: int, user: dict = Depends(get_current_user)):
    row = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
    log_event(user["name"], "human", "contract_deleted", contract_id=None,
              details={"name": row["name"]})
    return {"ok": True}


@router.get("/contracts/{contract_id}/clauses")
def contract_clauses(contract_id: int, user: dict = Depends(get_current_user)):
    return query("SELECT * FROM clauses WHERE contract_id = ? ORDER BY idx", (contract_id,))


@router.get("/contracts/{contract_id}/risks")
def contract_risks(contract_id: int, user: dict = Depends(get_current_user)):
    return query(
        "SELECT r.*, c.idx AS clause_idx, c.title AS clause_title, c.clause_type"
        " FROM risks r JOIN clauses c ON c.id = r.clause_id"
        " WHERE r.contract_id = ? ORDER BY c.idx",
        (contract_id,),
    )


@router.get("/contracts/{contract_id}/redlines")
def contract_redlines(contract_id: int, user: dict = Depends(get_current_user)):
    return query(
        "SELECT rl.*, c.idx AS clause_idx, c.clause_type, c.title AS clause_title"
        " FROM redlines rl JOIN clauses c ON c.id = rl.clause_id"
        " WHERE rl.contract_id = ? ORDER BY c.idx",
        (contract_id,),
    )


@router.put("/redlines/{redline_id}/decision")
def decide_redline(redline_id: int, decision: str = "accepted", user: dict = Depends(get_current_user)):
    redline = query_one("SELECT * FROM redlines WHERE id = ?", (redline_id,))
    if not redline:
        raise HTTPException(status_code=404, detail="Redline not found")
    status = "accepted" if decision == "accepted" else "rejected"
    execute("UPDATE redlines SET status = ? WHERE id = ?", (status, redline_id))
    log_event(
        user["name"], "human", f"redline_{status}",
        contract_id=redline["contract_id"],
        details={"redline_id": redline_id, "rule_id": redline["rule_id"]},
    )
    return {"id": redline_id, "status": status}


@router.post("/contracts/{contract_id}/review")
async def start_review(
    contract_id: int, payload: ReviewRequest, user: dict = Depends(get_current_user)
):
    from ..jobs import create_job, spawn
    from ..pipeline import run_review_job

    contract = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    job_id = create_job()
    spawn(job_id, lambda: run_review_job(job_id, contract_id, payload.company_playbook))
    log_event(user["name"], "human", "review_requested", contract_id=contract_id,
              details={"playbook": payload.company_playbook})
    return {"job_id": job_id}


@router.post("/contracts/{contract_id}/negotiate")
async def start_negotiation(
    contract_id: int, user: dict = Depends(get_current_user)
):
    from ..agents.negotiation import run_negotiation
    from ..jobs import create_job, spawn

    contract = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract["status"] == "negotiating":
        return {"already_running": True, "contract_id": contract_id}
    company_pb = contract["company_playbook"] or "startup-friendly"
    cpt_pb = contract["counterparty_playbook"] or "vendor-friendly"
    job_id = create_job()

    async def _job():
        await run_negotiation(contract, company_pb, cpt_pb)

    spawn(job_id, _job)
    log_event(user["name"], "human", "negotiation_requested", contract_id=contract_id)
    return {"job_id": job_id}


@router.get("/contracts/{contract_id}/negotiation")
def negotiation_transcript(contract_id: int, user: dict = Depends(get_current_user)):
    from ..agents.negotiation import get_messages, get_negotiation

    negotiation = get_negotiation(contract_id)
    if not negotiation:
        return {"negotiation": None, "messages": []}
    return {
        "negotiation": negotiation,
        "messages": get_messages(negotiation["id"]),
    }


@router.get("/samples")
def list_samples(user: dict = Depends(get_current_user)):
    samples = []
    for path in sorted(SAMPLE_CONTRACTS_DIR.iterdir()):
        if path.suffix.lower() not in (".txt", ".pdf"):
            continue
        samples.append(
            {
                "name": path.stem,
                "format": path.suffix.lstrip(".").lower(),
                "size": path.stat().st_size,
                "counterparty": SAMPLE_COUNTERPARTIES.get(
                    path.stem, path.stem.split("_")[0].replace("-", " ").title()
                ),
            }
        )
    return samples


@router.post("/samples/{name}/load")
def load_sample(name: str, user: dict = Depends(get_current_user)):
    matches = [
        p
        for p in SAMPLE_CONTRACTS_DIR.iterdir()
        if p.stem == name and p.suffix.lower() in (".txt", ".pdf")
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="Sample not found")
    path = matches[0]
    try:
        if path.suffix.lower() == ".pdf":
            text = extract_text(path.name, path.read_bytes())
        else:
            text = path.read_text(encoding="utf-8")
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    counterparty = SAMPLE_COUNTERPARTIES.get(
        name, name.split("_")[0].replace("-", " ").title()
    )
    display = name.replace("-", " ").replace("_", " — ").title()
    contract_id = execute(
        "INSERT INTO contracts (name, counterparty, filename, format, status,"
        " company_playbook, counterparty_playbook, full_text, created_at)"
        " VALUES (?, ?, ?, ?, 'uploaded', 'startup-friendly', 'vendor-friendly', ?, ?)",
        (display, counterparty, path.name, path.suffix.lstrip(".").lower(), text, utcnow()),
    )
    log_event(user["name"], "human", "sample_loaded",
              contract_id=contract_id, details={"sample": name})
    return query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
