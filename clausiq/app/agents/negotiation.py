"""T4 — Simulated Multi-Agent Negotiation.
Two independent agents (company vs. counterparty), each governed by its
own playbook, exchange proposals through a turn-taking controller until
they converge or hit an explicit impasse."""
import asyncio
import json

from ..audit import log_event
from ..config import MAX_NEGOTIATION_ROUNDS
from ..db import execute, query_one, utcnow
from ..llm import llm
from ..playbooks import get_playbook
from .gate import create_approval
from .redline import get_redlines
from .risk import strictly_satisfies


def _msg(negotiation_id: int, round_no: int, actor: str, kind: str, content: str, payload=None) -> dict:
    msg_id = execute(
        "INSERT INTO negotiation_messages (negotiation_id, round_no, actor, kind, content,"
        " payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            negotiation_id,
            round_no,
            actor,
            kind,
            content,
            json.dumps(payload or {}, ensure_ascii=False),
            utcnow(),
        ),
    )
    return {
        "id": msg_id,
        "negotiation_id": negotiation_id,
        "round_no": round_no,
        "actor": actor,
        "kind": kind,
        "content": content,
        "payload": payload or {},
    }


def _changes_payload(items: list[dict]) -> dict:
    return {
        "changes": [
            {
                "clause_idx": item["clause_idx"],
                "clause_type": item.get("clause_type", ""),
                "title": item.get("clause_title", ""),
                "original": item.get("original_text", ""),
                "proposed": item.get("proposed_text", ""),
                "rule_id": item.get("rule_id"),
            }
            for item in items
        ]
    }


def _local_negotiation(negotiation_id: int, redlines: list[dict], company_pb: dict, cpt_pb: dict) -> tuple[int, str, str]:
    """Deterministic fallback negotiation, table-driven by both playbooks."""
    company_rules = {r["clause_type"]: r for r in company_pb.get("rules", [])}
    cpt_rules = {r["clause_type"]: r for r in cpt_pb.get("rules", [])}
    issues = [r for r in redlines if r.get("rule_id")]

    # Round 1 — company opens with its full proposal set.
    proposal_lines = [
        f"{i + 1}. {item['clause_title']}: {item['justification']}"
        for i, item in enumerate(issues)
    ]
    _msg(
        negotiation_id, 1, "company", "proposal",
        "Opening proposal from "
        f"{company_pb.get('organization', 'the company')}: "
        + "; ".join(proposal_lines[:6]) + (" …" if len(proposal_lines) > 6 else ""),
        _changes_payload(issues),
    )
    counters, accepts = [], []
    for item in issues:
        cpt_rule = cpt_rules.get(item["clause_type"])
        if cpt_rule and not strictly_satisfies(item["proposed_text"], cpt_rule):
            counters.append(
                {
                    **item,
                    "proposed_text": cpt_rule.get("suggested_language", item["proposed_text"]),
                    "counter": True,
                }
            )
        else:
            accepts.append(item)
    content = (
        f"{cpt_pb.get('organization', 'Counterparty')} responds: accepts "
        f"{len(accepts)} change(s)"
        + (f", counters {len(counters)} change(s)." if counters else ", all changes accepted.")
    )
    _msg(
        negotiation_id, 1, "counterparty",
        "accept" if not counters else "counter",
        content, _changes_payload([*accepts, *counters]),
    )

    open_issues = counters
    final_round = 1
    for round_no in range(2, MAX_NEGOTIATION_ROUNDS + 1):
        if not open_issues:
            break
        final_round = round_no
        # Company's turn.
        company_moves, conceded = [], []
        for item in open_issues:
            company_rule = company_rules.get(item["clause_type"])
            if company_rule and strictly_satisfies(item["proposed_text"], company_rule):
                conceded.append(item)
            elif company_rule and company_rule.get("severity") != "critical" and round_no >= 3:
                conceded.append(item)
            else:
                company_moves.append(
                    {**item, "proposed_text": company_rule.get("suggested_language", item["proposed_text"])}
                )
        if conceded and not company_moves:
            _msg(
                negotiation_id, round_no, "company", "accept",
                f"Company agent accepts the remaining {len(conceded)} counter-proposal(s).",
                _changes_payload(conceded),
            )
            open_issues = []
            continue
        if company_moves:
            _msg(
                negotiation_id, round_no, "company", "counter",
                f"Company agent holds the line on {len(company_moves)} item(s): "
                + "; ".join(m["clause_title"] for m in company_moves) + ".",
                _changes_payload(company_moves),
            )
        # Counterparty's turn.
        counterparty_moves = []
        for item in company_moves:
            cpt_rule = cpt_rules.get(item["clause_type"])
            if cpt_rule and strictly_satisfies(item["proposed_text"], cpt_rule):
                accepts.append(item)
            elif cpt_rule and cpt_rule.get("severity") != "critical":
                accepts.append(item)  # vendor concedes on non-critical rules
            else:
                counterparty_moves.append(item)
        if counterparty_moves:
            _msg(
                negotiation_id, round_no, "counterparty", "reject",
                f"{cpt_pb.get('organization', 'Counterparty')} declines on "
                f"{len(counterparty_moves)} item(s): "
                + "; ".join(m["clause_title"] for m in counterparty_moves) + ".",
                _changes_payload(counterparty_moves),
            )
            open_issues = counterparty_moves
        else:
            open_issues = []
            _msg(
                negotiation_id, round_no, "counterparty", "accept",
                f"{cpt_pb.get('organization', 'Counterparty')} accepts the company's terms.",
                _changes_payload(company_moves),
            )

    if open_issues:
        status, outcome = "impasse", (
            f"Impasse after {final_round} rounds on: "
            + "; ".join(i["clause_title"] for i in open_issues)
            + ". Escalated to human review."
        )
        kind = "summary"
    else:
        status, outcome = "agreed", (
            f"Agreement reached after {final_round} round(s): all "
            f"{len(issues)} flagged issue(s) resolved within both playbooks."
        )
        kind = "summary"
    _msg(
        negotiation_id, final_round, "system", kind,
        outcome, {"status": status, "rounds": final_round},
    )
    return final_round, status, outcome


def _llm_negotiation(
    negotiation_id: int, redlines: list[dict], company_pb: dict, cpt_pb: dict,
    contract: dict, max_rounds: int,
) -> tuple[int, str, str] | None:
    company_system = (
        f"You are the negotiation agent representing {company_pb.get('organization')} "
        f"(playbook: {company_pb.get('name')}). Defend these rules as hard constraints:\n"
        + "\n".join(
            f"- [{r['id']}] {r['statement']} (severity: {r.get('severity')})"
            for r in company_pb.get("rules", [])
        )
        + "\nNegotiate over the company's redlines below. Never accept a term that violates "
        "a critical rule. Be pragmatic on warnings. Respond in STRICT JSON only: "
        '{"move":"propose|counter|accept|close","content":str,'
        '"changes":[{"clause_type":str,"title":str,"proposed":str}],"open_issues":int}.'
    )
    cpt_system = (
        f"You are the negotiation agent representing {cpt_pb.get('organization')} "
        f"(playbook: {cpt_pb.get('name')}). Defend these rules as hard constraints:\n"
        + "\n".join(
            f"- [{r['id']}] {r['statement']} (severity: {r.get('severity')})"
            for r in cpt_pb.get("rules", [])
        )
        + "\nRespond to the other side's proposals. Seek the best terms for your principal, "
        "but concede on non-critical items to converge. Respond in STRICT JSON only: "
        '{"move":"accept|counter|reject|close","content":str,'
        '"changes":[{"clause_type":str,"title":str,"proposed":str}],"open_issues":int}.'
    )
    issues = json.dumps(
        [
            {
                "clause_type": r.get("clause_type"),
                "title": r.get("clause_title"),
                "original": r.get("original_text"),
                "company_proposal": r.get("proposed_text"),
                "justification": r.get("justification"),
                "rule_id": r.get("rule_id"),
            }
            for r in redlines if r.get("rule_id")
        ],
        ensure_ascii=False,
    )
    transcript = [f"Contract: {contract.get('name')} with {contract.get('counterparty')}\nIssues: {issues}"]

    open_issues = len([r for r in redlines if r.get("rule_id")]) or 1
    for round_no in range(1, max_rounds + 1):
        context = "\n".join(transcript[-8:])
        company = llm.complete_json(company_system, context)
        if not company:
            return None
        _msg(
            negotiation_id, round_no, "company",
            "proposal" if round_no == 1 else company.get("move", "counter"),
            str(company.get("content", ""))[:2000],
            {"changes": company.get("changes", []), "open_issues": company.get("open_issues", 0)},
        )
        transcript.append(f"[Company] {company.get('content', '')}")
        open_issues = int(company.get("open_issues", open_issues))
        if open_issues <= 0:
            _msg(negotiation_id, round_no, "system", "summary",
                 "Counterparty accepted all terms.", {"status": "agreed"})
            return round_no, "agreed", "Agreement reached."
        cpt = llm.complete_json(cpt_system, "\n".join(transcript[-8:]))
        if not cpt:
            return None
        _msg(
            negotiation_id, round_no, "counterparty",
            cpt.get("move", "counter"),
            str(cpt.get("content", ""))[:2000],
            {"changes": cpt.get("changes", []), "open_issues": cpt.get("open_issues", 0)},
        )
        transcript.append(f"[Counterparty] {cpt.get('content', '')}")
        open_issues = int(cpt.get("open_issues", open_issues))
        if open_issues <= 0:
            _msg(negotiation_id, round_no, "system", "summary",
                 "Company accepted the final terms.", {"status": "agreed"})
            return round_no, "agreed", "Agreement reached."
    outcome = f"Impasse after {max_rounds} rounds; escalated to human review."
    _msg(negotiation_id, max_rounds, "system", "summary", outcome, {"status": "impasse"})
    return max_rounds, "impasse", outcome


async def run_negotiation(
    contract: dict, company_playbook_id: str, counterparty_playbook_id: str,
    max_rounds: int | None = None,
) -> dict:
    company_pb = get_playbook(company_playbook_id) or get_playbook("startup-friendly") or {}
    cpt_pb = get_playbook(counterparty_playbook_id) or get_playbook("vendor-friendly") or {}
    redlines = get_redlines(contract["id"])
    max_rounds = max_rounds or MAX_NEGOTIATION_ROUNDS

    negotiation_id = execute(
        "INSERT INTO negotiations (contract_id, company_playbook, counterparty_playbook,"
        " status, rounds, created_at) VALUES (?, ?, ?, 'running', 0, ?)",
        (contract["id"], company_playbook_id, counterparty_playbook_id, utcnow()),
    )
    execute("UPDATE contracts SET status = 'negotiating', company_playbook = ?,"
            " counterparty_playbook = ? WHERE id = ?",
            (company_playbook_id, counterparty_playbook_id, contract["id"]))
    _msg(
        negotiation_id, 0, "system", "note",
        f"Negotiation opened between {company_pb.get('organization', 'Company')} and "
        f"{cpt_pb.get('organization', 'Counterparty')}. {len(redlines)} issue(s) on the table.",
    )
    log_event(
        "Negotiation Controller", "agent", "negotiation_started",
        contract_id=contract["id"],
        details={"company_playbook": company_playbook_id,
                 "counterparty_playbook": counterparty_playbook_id},
    )

    result: tuple[int, str, str] | None = None
    if llm.enabled:
        result = await asyncio.to_thread(
            _llm_negotiation, negotiation_id, redlines, company_pb, cpt_pb,
            contract, max_rounds,
        )
    if result is None:
        result = await asyncio.to_thread(
            _local_negotiation, negotiation_id, redlines, company_pb, cpt_pb
        )
    rounds, status, outcome = result
    execute(
        "UPDATE negotiations SET status = ?, rounds = ?, outcome_summary = ? WHERE id = ?",
        (status, rounds, outcome, negotiation_id),
    )
    execute("UPDATE contracts SET status = 'negotiated' WHERE id = ?", (contract["id"],))
    log_event(
        "Negotiation Controller", "agent", "negotiation_completed",
        contract_id=contract["id"],
        details={"status": status, "rounds": rounds, "outcome": outcome},
    )

    # Route real-world actions through the approval gate.
    counterparty = contract["counterparty"]
    create_approval(
        contract["id"], f"Send negotiated redline package to {counterparty}",
        "send_external", "Deliver the final redline package to the counterparty for signature.",
        {"negotiation_id": negotiation_id},
    )
    create_approval(
        contract["id"], "Accept final negotiated terms",
        "accept_terms", "Lock the negotiated terms and move the contract to final.",
        {"negotiation_id": negotiation_id},
    )
    if status == "impasse":
        create_approval(
            contract["id"], "Escalate unresolved clauses to external counsel",
            "escalate_counsel", "Send the deadlocked clauses to external legal counsel for review.",
            {"negotiation_id": negotiation_id},
        )
    create_approval(
        contract["id"], "Save negotiation summary to the contract record",
        "internal_note", outcome, {"negotiation_id": negotiation_id},
    )
    return {
        "id": negotiation_id,
        "contract_id": contract["id"],
        "status": status,
        "rounds": rounds,
        "outcome_summary": outcome,
    }


def get_negotiation(contract_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM negotiations WHERE contract_id = ? ORDER BY id DESC LIMIT 1",
        (contract_id,),
    )


def get_messages(negotiation_id: int) -> list[dict]:
    rows = execute_placeholder(negotiation_id)
    return rows


def execute_placeholder(negotiation_id: int) -> list[dict]:
    from ..db import query

    return query(
        "SELECT * FROM negotiation_messages WHERE negotiation_id = ? ORDER BY id",
        (negotiation_id,),
    )
