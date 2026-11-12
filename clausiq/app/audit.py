"""Append-only audit trail with a chained SHA-256 hash per entry, making
the log tamper-evident: every entry commits to the hash of its predecessor."""
import hashlib
import json

from .db import query, query_one, execute, utcnow


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _chain_hash(prev_hash: str | None, payload: dict) -> str:
    digest = hashlib.sha256()
    digest.update((prev_hash or "GENESIS").encode("utf-8"))
    digest.update(_canonical(payload).encode("utf-8"))
    return digest.hexdigest()


def log_event(
    actor: str,
    actor_type: str,
    action_type: str,
    risk_tier: str = "info",
    contract_id: int | None = None,
    details: dict | None = None,
) -> dict:
    details = details or {}
    ts = utcnow()
    prev = query_one("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
    prev_hash = prev["hash"] if prev else None
    payload = {
        "ts": ts,
        "actor": actor,
        "actor_type": actor_type,
        "action_type": action_type,
        "risk_tier": risk_tier,
        "contract_id": contract_id,
        "details": details,
    }
    entry_hash = _chain_hash(prev_hash, payload)
    execute(
        "INSERT INTO audit_log (ts, actor, actor_type, action_type, risk_tier,"
        " contract_id, details, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ts,
            actor,
            actor_type,
            action_type,
            risk_tier,
            contract_id,
            json.dumps(details, ensure_ascii=False),
            prev_hash,
            entry_hash,
        ),
    )
    return {**payload, "hash": entry_hash}


def get_entries(contract_id: int | None = None, limit: int = 200, offset: int = 0) -> list[dict]:
    if contract_id is not None:
        rows = query(
            "SELECT * FROM audit_log WHERE contract_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (contract_id, limit, offset),
        )
    else:
        rows = query(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )
    entries = []
    verified = True
    for row in reversed(rows):
        entry = dict(row)
        entry["details"] = json.loads(entry["details"] or "{}")
        expected = _chain_hash(entry["prev_hash"], {
            "ts": entry["ts"], "actor": entry["actor"], "actor_type": entry["actor_type"],
            "action_type": entry["action_type"], "risk_tier": entry["risk_tier"],
            "contract_id": entry["contract_id"], "details": entry["details"],
        })
        entry["verified"] = bool(expected == entry["hash"]) and verified
        verified = verified and entry["verified"]
        entries.append(entry)
    return list(reversed(entries))
