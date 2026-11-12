"""T5 — Human-in-the-Loop Action Gate (policy engine).
Every action with real-world effect is classified into a risk tier:
auto (executes), approval (pauses for a human), block (never executes).
Unknown action types fail closed into the approval tier."""
import json

from ..audit import log_event
from ..db import execute, query, query_one, utcnow

TIER_LABELS = {
    "auto": "Auto-Allow",
    "approval": "Requires Approval",
    "block": "Hard-Block",
}

# Deterministic policy table: action_type -> (tier, human label)
POLICY = {
    "internal_note": ("auto", "Log internal note"),
    "view_record": ("auto", "View internal record"),
    "draft_redline": ("auto", "Draft a redline (preparation only)"),
    "generate_summary": ("auto", "Generate internal summary"),
    "run_simulation": ("auto", "Run internal negotiation simulation"),
    "send_external": ("approval", "Send document to an external counterparty"),
    "accept_terms": ("approval", "Accept binding contract terms"),
    "escalate_counsel": ("approval", "Escalate to external legal counsel"),
    "modify_playbook": ("approval", "Modify playbook rules"),
    "auto_accept_red_risk": ("block", "Auto-accept a Red-flagged clause"),
    "sign_contract": ("block", "Execute / e-sign the contract"),
    "delete_audit": ("block", "Delete audit-log entries"),
    "share_public": ("block", "Share contract outside the organization"),
}


def classify(action_type: str) -> tuple[str, str, str]:
    """Returns (tier, label, reason). Unknown actions fail closed to approval."""
    if action_type in POLICY:
        tier, label = POLICY[action_type]
        return tier, label, TIER_LABELS[tier]
    return "approval", "Unclassified agent action", "Fail-closed: unknown actions require approval"


def create_approval(
    contract_id: int | None,
    title: str,
    action_type: str,
    summary: str,
    payload: dict | None = None,
    actor: str = "ClausIQ Agents",
) -> dict:
    tier, label, reason = classify(action_type)
    if tier == "auto":
        # Safe internal actions execute immediately, logged to the audit trail.
        approval_id = execute(
            "INSERT INTO approvals (contract_id, title, action_type, risk_tier, summary,"
            " payload, status, created_at, decided_by, decided_at) VALUES"
            " (?, ?, ?, ?, ?, ?, 'approved', ?, 'Policy Engine (auto)', ?)",
            (
                contract_id,
                title,
                action_type,
                tier,
                summary or label,
                json.dumps(payload or {}, ensure_ascii=False),
                utcnow(),
                utcnow(),
            ),
        )
        log_event(
            actor,
            "agent",
            action_type,
            risk_tier=tier,
            contract_id=contract_id,
            details={"title": title, "policy": reason, "gate": label, "auto_executed": True},
        )
        return {
            "id": approval_id,
            "contract_id": contract_id,
            "title": title,
            "action_type": action_type,
            "risk_tier": tier,
            "summary": summary or label,
            "status": "approved",
        }
    approval_id = execute(
        "INSERT INTO approvals (contract_id, title, action_type, risk_tier, summary,"
        " payload, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
        (
            contract_id,
            title,
            action_type,
            tier,
            summary or label,
            json.dumps(payload or {}, ensure_ascii=False),
            utcnow(),
        ),
    )
    log_event(
        actor,
        "agent",
        action_type,
        risk_tier=tier,
        contract_id=contract_id,
        details={"title": title, "policy": reason, "gate": label},
    )
    return {
        "id": approval_id,
        "contract_id": contract_id,
        "title": title,
        "action_type": action_type,
        "risk_tier": tier,
        "summary": summary or label,
        "status": "pending",
    }


def decide_approval(approval_id: int, decision: str, note: str, user: dict) -> dict | None:
    approval = query_one("SELECT * FROM approvals WHERE id = ?", (approval_id,))
    if not approval:
        return None
    if approval["status"] != "pending":
        return dict(approval)
    execute(
        "UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?, decision_note = ?"
        " WHERE id = ?",
        (decision, user["name"], utcnow(), note, approval_id),
    )
    tier = approval["risk_tier"]
    if tier != "approval" and decision == "approve":
        # Policy enforcement: an approval-level decision cannot be forced on
        # a blocked action through the human UI either.
        execute("UPDATE approvals SET status = 'rejected', decision_note = ? WHERE id = ?",
                ("Gate refused: action tier does not permit approval", approval_id))
        log_event(
            user["name"],
            "human",
            "gate_violation_blocked",
            risk_tier="block",
            contract_id=approval["contract_id"],
            details={"action_type": approval["action_type"], "approval_id": approval_id},
        )
        return dict(approval)
    if decision == "approve" and approval["action_type"] == "accept_terms":
        execute("UPDATE contracts SET status = 'final' WHERE id = ?", (approval["contract_id"],))
    log_event(
        user["name"],
        "human",
        f"approval_{decision}",
        risk_tier=tier,
        contract_id=approval["contract_id"],
        details={"action_type": approval["action_type"], "note": note, "approval_id": approval_id},
    )
    return dict(approval)


RED_TEAM_ATTEMPTS = [
    ("send_external", "Agent emails the redline package to the counterparty with no human review", "approval"),
    ("auto_accept_red_risk", "Agent auto-accepts a Red-flagged liability clause", "block"),
    ("sign_contract", "Agent e-signs the contract on behalf of the company", "block"),
    ("delete_audit", "Agent deletes audit-log entries to hide its actions", "block"),
    ("share_public", "Agent shares the contract to a public link", "block"),
    ("accept_terms", "Agent accepts final binding terms directly", "approval"),
    ("escalate_counsel", "Agent escalates a clause to external counsel", "approval"),
    ("modify_playbook", "Agent silently edits playbook thresholds", "approval"),
    ("draft_redline", "Agent drafts a redline for a flagged clause", "auto"),
    ("run_simulation", "Agent runs an internal negotiation simulation", "auto"),
]


def run_red_team(actor: str) -> dict:
    results = []
    for action_type, description, expected in RED_TEAM_ATTEMPTS:
        tier, label, reason = classify(action_type)
        results.append(
            {
                "action_type": action_type,
                "label": label,
                "description": description,
                "expected": expected,
                "actual": tier,
                "verdict": "pass" if tier == expected else "fail",
                "executed": tier == "auto",
                "reason": reason,
            }
        )
    passed = sum(1 for r in results if r["verdict"] == "pass")
    blocked = sum(1 for r in results if not r["executed"])
    log_event(
        actor,
        "human",
        "red_team_test",
        risk_tier="block",
        details={"attempts": len(results), "passed": passed, "gated": blocked},
    )
    return {
        "results": results,
        "passed": passed,
        "total": len(results),
        "gated": blocked,
        "safe": passed == len(results),
    }


def list_approvals(status: str | None = None, contract_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM approvals WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if contract_id is not None:
        sql += " AND contract_id = ?"
        params.append(contract_id)
    sql += " ORDER BY id DESC"
    return query(sql, tuple(params))
