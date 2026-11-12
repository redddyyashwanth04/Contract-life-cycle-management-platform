"""Pydantic request models."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class ContractCreate(BaseModel):
    name: str
    counterparty: str = "Counterparty"
    text: str | None = None
    company_playbook: str = "startup-friendly"
    counterparty_playbook: str = "vendor-friendly"


class ReviewRequest(BaseModel):
    company_playbook: str = "startup-friendly"


class NegotiateRequest(BaseModel):
    company_playbook: str = "startup-friendly"
    counterparty_playbook: str = "vendor-friendly"
    max_rounds: int | None = None


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str = ""
