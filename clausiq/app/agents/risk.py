"""T2 — Playbook-Based Risk Classification.
Every verdict is grounded in a specific playbook rule so each flag is
traceable to (clause text, rule id). LLM path reasons over retrieved
rules; fallback path evaluates patterns deterministically."""
import asyncio
import json
import re

from ..audit import log_event
from ..db import execute, query
from ..llm import llm
from ..playbooks import get_playbook


def rule_eval(text: str, rule: dict) -> tuple[str, str, str | None, float]:
    lowered = text.lower()
    for pattern in rule.get("forbidden_patterns", []):
        match = re.search(re.escape(pattern), lowered)
        if match:
            level = "red" if rule.get("severity") == "critical" else "yellow"
            return (
                level,
                f"Contains '{match.group(0)}', which violates {rule['id']}: {rule['statement']}",
                pattern,
                0.97,
            )
    for pattern in rule.get("preferred_patterns", []):
        match = re.search(re.escape(pattern), lowered)
        if match:
            return (
                "green",
                f"Satisfies {rule['id']}: {rule['statement']}",
                pattern,
                0.94,
            )
    for pattern in rule.get("required_patterns", []):
        if not re.search(re.escape(pattern), lowered):
            level = "red" if rule.get("severity") == "critical" else "yellow"
            return (
                level,
                f"Missing required element for {rule['id']}: {rule['statement']}",
                pattern,
                0.9,
            )
    for pattern in rule.get("ambiguous_patterns", []):
        if re.search(re.escape(pattern), lowered):
            return (
                "yellow",
                f"Wording is ambiguous against {rule['id']} and needs review.",
                pattern,
                0.8,
            )
    return "green", f"No violation detected for {rule['id']}.", None, 0.76


def strictly_satisfies(text: str, rule: dict) -> bool:
    lowered = text.lower()
    for pattern in rule.get("forbidden_patterns", []):
        if re.search(re.escape(pattern), lowered):
            return False
    preferred = rule.get("preferred_patterns", [])
    if preferred:
        return any(re.search(re.escape(p), lowered) for p in preferred)
    required = rule.get("required_patterns", [])
    return all(re.search(re.escape(r), lowered) for r in required) if required else True


def _llm_evaluate_batch(clauses: list[dict], rules_by_type: dict[str, list[dict]]) -> dict | None:
    brief = []
    for clause in clauses:
        rules = rules_by_type.get(clause["clause_type"], [])
        brief.append(
            {
                "clause_idx": clause["idx"],
                "clause_type": clause["clause_type"],
                "text": clause["text"][:2500],
                "rules": [
                    {"id": r["id"], "statement": r["statement"], "severity": r.get("severity")}
                    for r in rules
                ],
            }
        )
    system = (
        "You are the risk-classification agent of ClausIQ. Judge each clause against ONLY the "
        "playbook rules supplied for its clause type. Rules:\n"
        "1. risk_level must be one of: green (compliant), yellow (negotiable/ambiguous), "
        "red (violates a critical rule).\n"
        "2. If you flag yellow or red you MUST cite the exact rule_id that triggered it and "
        "explain why in one sentence.\n"
        "3. Never invent rules. If no supplied rule applies, risk_level is green with "
        'rule_id null and an explanation saying so.\n'
        "4. Respond with STRICT JSON only: "
        '{"verdicts":[{"clause_idx":int,"risk_level":str,"rule_id":str|null,'
        '"explanation":str,"confidence":float}]}.'
    )
    result = llm.complete_json(system, json.dumps({"clauses": brief}, ensure_ascii=False))
    return result if isinstance(result, dict) else None


async def evaluate_contract(contract: dict, clauses: list[dict], playbook_id: str) -> list[dict]:
    playbook = get_playbook(playbook_id) or {}
    rules = playbook.get("rules", [])
    rules_by_type: dict[str, list[dict]] = {}
    for rule in rules:
        rules_by_type.setdefault(rule["clause_type"], []).append(rule)

    verdicts: dict[int, dict] = {}
    if llm.enabled:
        for start in range(0, len(clauses), 8):
            batch = clauses[start : start + 8]
            result = await asyncio.to_thread(_llm_evaluate_batch, batch, rules_by_type)
            if not result:
                verdicts = {}
                break
            for verdict in result.get("verdicts", []):
                idx = int(verdict.get("clause_idx", -1))
                verdicts[idx] = verdict

    execute("DELETE FROM risks WHERE contract_id = ?", (contract["id"],))
    rows = []
    for clause in clauses:
        if clause["idx"] in verdicts:
            verdict = verdicts[clause["idx"]]
            level = verdict.get("risk_level", "green")
            if level not in {"green", "yellow", "red"}:
                level = "yellow"
            rule_id = verdict.get("rule_id")
            rule = next((r for r in rules if r["id"] == rule_id), None)
            explanation = str(verdict.get("explanation") or "No explanation provided.")
            confidence = float(verdict.get("confidence") or 0.7)
        else:
            applicable = rules_by_type.get(clause["clause_type"], [])
            if applicable:
                level, explanation, matched, confidence = rule_eval(clause["text"], applicable[0])
                for rule in applicable[1:]:
                    candidate = rule_eval(clause["text"], rule)
                    rank = {"green": 0, "yellow": 1, "red": 2}
                    if rank[candidate[0]] > rank[level]:
                        level, explanation, matched, confidence = candidate
                rule = applicable[0]
            else:
                level, explanation, matched, confidence = (
                    "green",
                    f"No playbook rule applies to {clause['clause_type']} clauses.",
                    None,
                    0.7,
                )
                rule = None
            rule_id = rule["id"] if rule else None

        risk_id = execute(
            "INSERT INTO risks (contract_id, clause_id, risk_level, rule_id, rule_name,"
            " rule_text, explanation, confidence, matched)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                contract["id"],
                clause["id"],
                level,
                rule_id,
                rule["name"] if rule else None,
                rule["statement"] if rule else None,
                explanation,
                confidence,
                None,
            ),
        )
        rows.append(
            {
                "id": risk_id,
                "contract_id": contract["id"],
                "clause_id": clause["id"],
                "clause_idx": clause["idx"],
                "risk_level": level,
                "rule_id": rule_id,
                "rule_name": rule["name"] if rule else None,
                "rule_text": rule["statement"] if rule else None,
                "explanation": explanation,
                "confidence": round(confidence, 2),
            }
        )

    counts = {
        level: sum(1 for r in rows if r["risk_level"] == level)
        for level in ("green", "yellow", "red")
    }
    log_event(
        "Risk Classifier",
        "agent",
        "risks_classified",
        contract_id=contract["id"],
        details={"counts": counts, "playbook": playbook_id},
    )
    return rows


def get_risks(contract_id: int) -> list[dict]:
    return query(
        "SELECT r.*, c.idx AS clause_idx, c.title AS clause_title FROM risks r"
        " JOIN clauses c ON c.id = r.clause_id"
        " WHERE r.contract_id = ? ORDER BY c.idx",
        (contract_id,),
    )
