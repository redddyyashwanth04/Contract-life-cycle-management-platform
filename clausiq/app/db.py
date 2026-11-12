"""SQLite storage layer. One connection per operation keeps the async
background jobs simple and safe; WAL mode handles concurrent access."""
import hashlib
import secrets
import sqlite3
import threading
from datetime import datetime, timezone

from .config import DATA_DIR, DB_PATH

_write_lock = threading.Lock()


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    organization TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    counterparty TEXT NOT NULL,
    filename TEXT,
    format TEXT,
    status TEXT NOT NULL DEFAULT 'uploaded',
    company_playbook TEXT,
    counterparty_playbook TEXT,
    summary TEXT,
    full_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    clause_type TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    source_ref TEXT
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_id INTEGER NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
    risk_level TEXT NOT NULL,
    rule_id TEXT,
    rule_name TEXT,
    rule_text TEXT,
    explanation TEXT,
    confidence REAL,
    matched TEXT
);

CREATE TABLE IF NOT EXISTS redlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_id INTEGER NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    proposed_text TEXT NOT NULL,
    justification TEXT,
    rule_id TEXT,
    status TEXT NOT NULL DEFAULT 'proposed'
);

CREATE TABLE IF NOT EXISTS negotiations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    company_playbook TEXT,
    counterparty_playbook TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    rounds INTEGER NOT NULL DEFAULT 0,
    outcome_summary TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS negotiation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negotiation_id INTEGER NOT NULL REFERENCES negotiations(id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL,
    actor TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER REFERENCES contracts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    action_type TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    summary TEXT,
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    action_type TEXT NOT NULL,
    risk_tier TEXT NOT NULL DEFAULT 'info',
    contract_id INTEGER,
    details TEXT NOT NULL DEFAULT '{}',
    prev_hash TEXT,
    hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clauses_contract ON clauses(contract_id);
CREATE INDEX IF NOT EXISTS idx_risks_contract ON risks(contract_id);
CREATE INDEX IF NOT EXISTS idx_redlines_contract ON redlines(contract_id);
CREATE INDEX IF NOT EXISTS idx_msgs_negotiation ON negotiation_messages(negotiation_id);
CREATE INDEX IF NOT EXISTS idx_audit_contract ON audit_log(contract_id);
"""


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + "::" + password).encode("utf-8")).hexdigest()


def verify_password(password: str, stored: str) -> bool:
    salt, _, digest = stored.partition("$")
    return _hash_password(password, salt) == digest


def make_password(password: str) -> str:
    salt = secrets.token_hex(8)
    return f"{salt}${_hash_password(password, salt)}"


SEED_USERS = [
    ("Yashwanth Reddy", "yash@nimbus.app", "demo123", "Founder", "Nimbus Labs"),
    ("Maya Krishnan", "maya@nimbus.app", "demo123", "Legal Reviewer", "Nimbus Labs"),
    ("ClausIQ Admin", "admin@clausiq.io", "admin123", "Administrator", "ClausIQ"),
]


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        conn = get_conn()
        try:
            conn.executescript(SCHEMA)
            for name, email, pw, role, org in SEED_USERS:
                exists = conn.execute(
                    "SELECT 1 FROM users WHERE email = ?", (email,)
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO users (name, email, password_hash, role, organization)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (name, email, make_password(pw), role, org),
                    )
            conn.commit()
        finally:
            conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    with _write_lock:
        conn = get_conn()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
