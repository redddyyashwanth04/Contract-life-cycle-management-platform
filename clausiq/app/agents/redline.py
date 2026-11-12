"""T3 — Justified Redline Generation.
Produces surgical, diffable rewrites for every yellow/red clause with a
one-sentence justification citing the playbook rule."""
import asyncio
import json

from ..audit import log_event
from ..db import execute, query
from ..llm import llm
from ..playbooks import get_playbook


def _llm_draft_batch(items: list[dict]) -> dict | None:
    system = (
        "You are the redline-drafting agent of ClausIQ. For each flagged clause, draft a "
        "MINIMAL, surgical rewrite that fixes exactly the issue flagged, keeps the rest of "
        "the clause intact, and remains enforceable and coherent. Rules:\n"
        "1. Never rewrite the whole contract - only the flagged clause.\n"
        "2. Add a one-sentence justification citing the playbook rule id and the change.\n"
        "3. If a suggested_language is supplied, align your wording with it.\n"
        "4. Respond with STRICT JSON only: "
        '{"redlines":[{"clause_idx":int,"proposed_text":str,"justification":str}]}.'
    )
    result = llm.complete_json(system, json.dumps({"items": items}, ensure_ascii=False))
    return result if isinstance(result, dict) else None


async def draft_redlines(
    contract: dict, clauses: list[dict], risks: list[dict], playbook_id: str
) -> list[dict]:
    playbook = get_playbook(playbook_id) or {}
    rules = {r["id"]: r for r in playbook.get("rules", [])}
    flagged = [r for r in risks if r["risk_level"] in {"yellow", "red"}]
    clause_by_idx = {c["idx"]: c for c in clauses}

    llm_out: dict[int, dict] = {}
    if llm.enabled and flagged:
        for start in range(0, len(flagged), 5):
            batch = flagged[start : start + 5]
            items = []
            for risk in batch:
                clause = clause_by_idx.get(risk["clause_idx"])
                rule = rules.get(risk["rule_id"], {})
                items.append(
                    {
                        "clause_idx": risk["clause_idx"],
                        "clause_type": clause["clause_type"] if clause else "",
                        "risk_level": risk["risk_level"],
                        "original_text": clause["text"] if clause else "",
                        "rule_id": risk["rule_id"],
                        "rule_statement": risk["rule_text"],
                        "suggested_language": rule.get("suggested_language", ""),
                    }
                )
            result = await asyncio.to_thread(_llm_draft_batch, items)
            if not result:
                llm_out = {}
                break
            for item in result.get("redlines", []):
                llm_out[int(item.get("clause_idx", -1))] = item

    execute("DELETE FROM redlines WHERE contract_id = ?", (contract["id"],))
    rows = []
    for risk in flagged:
        clause = clause_by_idx[risk["clause_idx"]]
        rule = rules.get(risk["rule_id"], {})
        if risk["clause_idx"] in llm_out:
            item = llm_out[risk["clause_idx"]]
            proposed = str(item.get("proposed_text") or "").strip()
            justification = str(item.get("justification") or "").strip()
            if not proposed:
                proposed, justification = (
                    rule.get("suggested_language", clause["text"]),
                    rule.get("redline_notes", ""),
                )
        else:
            proposed = rule.get("suggested_language", clause["text"])
            justification = rule.get("redline_notes", "Align clause with the playbook rule.")

        redline_id = execute(
            "INSERT INTO redlines (contract_id, clause_id, original_text, proposed_text,"
            " justification, rule_id, status) VALUES (?, ?, ?, ?, ?, ?, 'proposed')",
            (
                contract["id"],
                clause["id"],
                clause["text"],
                proposed,
                justification,
                risk["rule_id"],
            ),
        )
        rows.append(
            {
                "id": redline_id,
                "contract_id": contract["id"],
                "clause_id": clause["id"],
                "clause_idx": clause["idx"],
                "clause_type": clause["clause_type"],
                "clause_title": clause["title"],
                "original_text": clause["text"],
                "proposed_text": proposed,
                "justification": justification,
                "rule_id": risk["rule_id"],
                "status": "proposed",
            }
        )

    log_event(
        "Redline Drafter",
        "agent",
        "redlines_drafted",
        contract_id=contract["id"],
        details={"count": len(rows), "targets": "yellow+red clauses"},
    )
    return rows


def get_redlines(contract_id: int) -> list[dict]:
    return query(
        "SELECT rl.*, c.idx AS clause_idx, c.clause_type, c.title AS clause_title"
        " FROM redlines rl JOIN clauses c ON c.id = rl.clause_id"
        " WHERE rl.contract_id = ? ORDER BY c.idx",
        (contract_id,),
    )
