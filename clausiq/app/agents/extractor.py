"""T1 — Clause Extraction & Structuring.
LLM-driven extraction with a deterministic heuristic fallback, so the
platform stays fully demonstrable even without an API key."""
import asyncio
import json

from ..audit import log_event
from ..db import execute, query
from ..llm import llm
from .base import CLAUSE_TYPES, infer_clause_type, split_sections

MAX_LLM_CHARS = 60000

SYSTEM_PROMPT = (
    "You are the clause-extraction agent of ClausIQ, a governed contract-intelligence "
    "platform. Your job is to segment an unreviewed commercial contract into its "
    "individual clauses and sections. Rules:\n"
    "1. Preserve the EXACT verbatim text of each clause - never summarize or rewrite.\n"
    "2. Assign each clause one clause_type from the allowed list.\n"
    "3. Keep clauses atomic: one topic per clause, but do not split sentences mid-way.\n"
    "4. Include a short human-readable title and the source reference (section number) "
    "where it exists.\n"
    "5. Respond with STRICT JSON only: "
    '{"clauses":[{"title":str,"clause_type":str,"text":str,"source_ref":str}]}.'
)


def _llm_extract(text: str) -> list[dict] | None:
    payload = json.dumps(
        {
            "allowed_clause_types": CLAUSE_TYPES,
            "contract_text": text[:MAX_LLM_CHARS],
        },
        ensure_ascii=False,
    )
    result = llm.complete_json(SYSTEM_PROMPT, payload)
    if not result:
        return None
    clauses = result.get("clauses") if isinstance(result, dict) else None
    if not isinstance(clauses, list) or not clauses:
        return None
    cleaned = []
    for item in clauses:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        clause_type = str(item.get("clause_type", "General"))
        if clause_type not in CLAUSE_TYPES:
            clause_type = infer_clause_type(str(item.get("text", "")))
        cleaned.append(
            {
                "title": str(item.get("title") or clause_type)[:120],
                "clause_type": clause_type,
                "text": str(item["text"]).strip(),
                "source_ref": str(item.get("source_ref") or "")[:80],
            }
        )
    return cleaned or None


def _fallback_extract(text: str) -> list[dict]:
    sections = split_sections(text)
    return [
        {
            "title": section["title"],
            "clause_type": infer_clause_type(
                f"{section.get('heading', '')} {section['title']} {section['text']}"
            ),
            "text": section["text"],
            "source_ref": section["source_ref"],
        }
        for section in sections
    ]


async def extract_contract(contract: dict) -> list[dict]:
    text = contract["full_text"]
    clauses: list[dict] | None = None
    engine = "local-fallback"
    if llm.enabled:
        clauses = await asyncio.to_thread(_llm_extract, text)
    if clauses is None:
        clauses = _fallback_extract(text)
    else:
        engine = "groq"

    execute("DELETE FROM clauses WHERE contract_id = ?", (contract["id"],))
    stored = []
    for idx, clause in enumerate(clauses):
        clause_id = execute(
            "INSERT INTO clauses (contract_id, idx, clause_type, title, text, source_ref)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                contract["id"],
                idx,
                clause["clause_type"],
                clause["title"],
                clause["text"],
                clause["source_ref"],
            ),
        )
        stored.append({**clause, "id": clause_id, "idx": idx, "contract_id": contract["id"]})

    log_event(
        "Clause Extractor",
        "agent",
        "clauses_extracted",
        contract_id=contract["id"],
        details={
            "count": len(stored),
            "engine": engine,
        },
    )
    return stored


def get_clauses(contract_id: int) -> list[dict]:
    return query(
        "SELECT * FROM clauses WHERE contract_id = ? ORDER BY idx", (contract_id,)
    )
