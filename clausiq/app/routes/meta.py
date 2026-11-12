from fastapi import APIRouter, Depends

from .. import __version__
from ..config import APP_NAME, APP_TAGLINE, DATA_DIR
from ..db import query, query_one
from ..llm import llm
from ..playbooks import list_playbooks
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/playbooks")
def playbooks(user: dict = Depends(get_current_user)):
    return list_playbooks()


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: dict = Depends(get_current_user)):
    from ..jobs import JOBS

    job = JOBS.get(job_id)
    if not job:
        return {"id": job_id, "status": "unknown"}
    return job


@router.get("/settings")
def settings(user: dict = Depends(get_current_user)):
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": __version__,
        "model": {
            "provider": llm.provider,
            "model": llm.model,
            "key_set": bool(llm.enabled),
            "mode": "groq" if llm.enabled else "demo-fallback",
        },
        "data_dir": str(DATA_DIR),
    }


@router.get("/dashboard")
def dashboard(user: dict = Depends(get_current_user)):
    contracts = query_one("SELECT COUNT(*) AS n FROM contracts")
    clauses = query_one("SELECT COUNT(*) AS n FROM clauses")
    risks = query_one(
        "SELECT SUM(risk_level='red') AS red, SUM(risk_level='yellow') AS yellow,"
        " SUM(risk_level='green') AS green FROM risks"
    )
    pending = query_one("SELECT COUNT(*) AS n FROM approvals WHERE status='pending'")
    negotiations = query_one("SELECT COUNT(*) AS n FROM negotiations")
    audits = query_one("SELECT COUNT(*) AS n FROM audit_log")
    recent = query(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT 8"
    )
    red_team = query_one(
        "SELECT details FROM audit_log WHERE action_type='red_team_test'"
        " ORDER BY id DESC LIMIT 1"
    )
    return {
        "counts": {
            "contracts": contracts["n"],
            "clauses": clauses["n"],
            "red": risks["red"] or 0,
            "yellow": risks["yellow"] or 0,
            "green": risks["green"] or 0,
            "pending_approvals": pending["n"],
            "negotiations": negotiations["n"],
            "audit_events": audits["n"],
        },
        "recent": recent,
        "last_red_team": red_team["details"] if red_team else None,
    }
