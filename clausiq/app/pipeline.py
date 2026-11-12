"""End-to-end orchestration: T1 -> T2 -> T3 with progress reporting and
audit events at every stage."""
import asyncio

from .agents.extractor import extract_contract
from .agents.redline import draft_redlines
from .agents.risk import evaluate_contract
from .audit import log_event
from .db import execute, query_one
from .jobs import JOBS, set_stage
from .llm import llm


async def summarize_contract(contract: dict, risks: list[dict]) -> str:
    counts = {
        level: sum(1 for r in risks if r["risk_level"] == level)
        for level in ("green", "yellow", "red")
    }
    fallback = (
        f"Reviewed {len(risks)} clause(s): {counts['green']} compliant, "
        f"{counts['yellow']} negotiable, {counts['red']} high-risk. "
        "High-risk clauses require redlines before signing; negotiable items should be "
        "addressed with the counterparty."
    )
    if not llm.enabled:
        return fallback
    system = (
        "You are the summarization agent of ClausIQ. Write a 2-3 sentence executive summary "
        "of this contract review for a busy founder. Lead with the headline risk level, name "
        "the most important red flags, and recommend a next step. Respond with STRICT JSON "
        'only: {"summary":str}.'
    )
    brief = [
        {"type": r.get("clause_type"), "level": r["risk_level"], "why": r["explanation"]}
        for r in risks
        if r["risk_level"] != "green"
    ][:12]
    import json

    result = await asyncio.to_thread(
        llm.complete_json,
        system,
        json.dumps({"counts": counts, "flags": brief}, ensure_ascii=False),
    )
    if result and result.get("summary"):
        return str(result["summary"])
    return fallback


async def run_review_job(job_id: str, contract_id: int, company_playbook: str) -> None:
    stages = ["Extracting clauses", "Classifying risks", "Drafting redlines", "Summarizing"]
    set_stage(job_id, stages[0], 0, len(stages))
    contract = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        raise ValueError("Contract not found")
    execute(
        "UPDATE contracts SET status = 'reviewing', company_playbook = ? WHERE id = ?",
        (company_playbook, contract_id),
    )
    log_event(
        "Review Orchestrator", "agent", "review_started",
        contract_id=contract_id, details={"playbook": company_playbook},
    )
    contract = {**contract, "company_playbook": company_playbook}

    set_stage(job_id, stages[0], 0, len(stages))
    clauses = await extract_contract(contract)

    set_stage(job_id, stages[1], 1, len(stages))
    risks = await evaluate_contract(contract, clauses, company_playbook)

    set_stage(job_id, stages[2], 2, len(stages))
    redlines = await draft_redlines(contract, clauses, risks, company_playbook)

    set_stage(job_id, stages[3], 3, len(stages))
    summary = await summarize_contract(contract, risks)
    execute("UPDATE contracts SET status = 'reviewed', summary = ? WHERE id = ?",
            (summary, contract_id))
    log_event(
        "Review Orchestrator", "agent", "review_completed",
        contract_id=contract_id,
        details={
            "clauses": len(clauses),
            "red": sum(1 for r in risks if r["risk_level"] == "red"),
            "yellow": sum(1 for r in risks if r["risk_level"] == "yellow"),
            "redlines": len(redlines),
        },
    )
    JOBS[job_id]["result"] = {
        "contract_id": contract_id,
        "clause_count": len(clauses),
        "risk_counts": {
            level: sum(1 for r in risks if r["risk_level"] == level)
            for level in ("green", "yellow", "red")
        },
        "redline_count": len(redlines),
        "summary": summary,
    }
