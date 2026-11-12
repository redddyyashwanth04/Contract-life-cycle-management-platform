"""Dummy but realistic authentication: seeded local accounts, hashed
passwords, bearer-token sessions with expiry kept in memory."""
import secrets
import time

from fastapi import Depends, Header, HTTPException

from .config import SESSION_TTL_SECONDS
from .db import query_one, verify_password

SESSIONS: dict[str, dict] = {}


def create_session(user: dict) -> str:
    token = secrets.token_hex(32)
    SESSIONS[token] = {
        "user_id": user["id"],
        "expires": time.time() + SESSION_TTL_SECONDS,
    }
    return token


def drop_session(token: str) -> None:
    SESSIONS.pop(token, None)


def get_current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    session = SESSIONS.get(token)
    if not session or session["expires"] < time.time():
        SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired")
    user = query_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def authenticate(email: str, password: str) -> dict | None:
    user = query_one("SELECT * FROM users WHERE lower(email) = lower(?)", (email,))
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user
